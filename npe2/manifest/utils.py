from __future__ import annotations

import json
import re
import site
import sys
import tempfile
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache, total_ordering
from io import BytesIO
from logging import getLogger
from pathlib import Path
from subprocess import run
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    SupportsInt,
    Tuple,
    TypeVar,
    Union,
)
from urllib.request import urlopen
from zipfile import ZipFile

from build.env import IsolatedEnvBuilder

if TYPE_CHECKING:
    from npe2.manifest.schema import PluginManifest
    from subprocess import _FILE

from ..types import PythonName

if TYPE_CHECKING:
    from typing_extensions import Protocol

    from .._command_registry import CommandRegistry
    from .contributions import ContributionPoints

    class ProvidesCommand(Protocol):
        command: str

        def get_callable(self, _registry: Optional[CommandRegistry] = None):
            ...


logger = getLogger(__name__)


def v1_to_v2(path):
    if isinstance(path, list):
        return path, True
    else:
        return [path], False


def v2_to_v1(paths, stack):
    if stack:
        return paths
    else:
        assert len(paths) == 1
        return paths[0]


R = TypeVar("R")
SHIM_NAME_PREFIX = "__npe1shim__."


# TODO: add ParamSpec when it's supported better by mypy
class Executable(Generic[R]):
    command: str

    def exec(
        self: ProvidesCommand,
        args: tuple = (),
        kwargs: dict = None,
        _registry: Optional[CommandRegistry] = None,
    ) -> R:
        if kwargs is None:
            kwargs = {}
        return self.get_callable(_registry)(*args, **kwargs)

    def get_callable(
        self: ProvidesCommand,
        _registry: Optional[CommandRegistry] = None,
    ) -> Callable[..., R]:
        if _registry is None:
            from .._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.get(self.command)

    @property
    def plugin_name(self: ProvidesCommand):
        # takes advantage of the fact that command always starts with manifest.name
        return self.command.split(".")[0]


@total_ordering
@dataclass
class Version:
    """A semver compatible version class.

    mostly vendored from python-semver (BSD-3):
    https://github.com/python-semver/python-semver/
    """

    major: SupportsInt
    minor: SupportsInt = 0
    patch: SupportsInt = 0
    prerelease: Union[bytes, str, int, None] = None
    build: Union[bytes, str, int, None] = None

    _SEMVER_PATTERN = re.compile(
        r"""
            ^
            (?P<major>0|[1-9]\d*)
            \.
            (?P<minor>0|[1-9]\d*)
            \.
            (?P<patch>0|[1-9]\d*)
            (?:-(?P<prerelease>
                (?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
                (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*
            ))?
            (?:\+(?P<build>
                [0-9a-zA-Z-]+
                (?:\.[0-9a-zA-Z-]+)*
            ))?
            $
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(cls, version: Union[bytes, str]) -> Version:
        """Convert string or bytes into Version object."""
        if isinstance(version, bytes):
            version = version.decode("UTF-8")
        match = cls._SEMVER_PATTERN.match(version)
        if match is None:
            raise ValueError(f"{version} is not valid SemVer string")
        matched_version_parts: Dict[str, Any] = match.groupdict()
        return cls(**matched_version_parts)

    # NOTE: we're only comparing the numeric parts for now.
    # ALSO: the rest of the comparators come  from functools.total_ordering
    def __eq__(self, other) -> bool:
        return self.to_tuple()[:3] == self._from_obj(other).to_tuple()[:3]

    def __lt__(self, other) -> bool:
        return self.to_tuple()[:3] < self._from_obj(other).to_tuple()[:3]

    @classmethod
    def _from_obj(cls, other):
        if isinstance(other, (str, bytes)):
            other = Version.parse(other)
        elif isinstance(other, dict):
            other = Version(**other)
        elif isinstance(other, (tuple, list)):
            other = Version(*other)
        elif not isinstance(other, Version):
            raise TypeError(
                f"Expected str, bytes, dict, tuple, list, or {cls} instance, "
                f"but got {type(other)}"
            )
        return other

    def to_tuple(self) -> Tuple[int, int, int, Optional[str], Optional[str]]:
        """Return version as tuple (first three are int, last two Opt[str])."""
        return (
            int(self.major),
            int(self.minor),
            int(self.patch),
            str(self.prerelease) if self.prerelease is not None else None,
            str(self.build) if self.build is not None else None,
        )

    def __iter__(self):
        yield from self.to_tuple()

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:  # pragma: no cover
            v += str(self.prerelease)
        if self.build:  # pragma: no cover
            v += str(self.build)
        return v


def _import_npe1_shim(shim_name: str) -> Any:
    """Import npe1 shimmed python_name

    Some objects returned by npe1 hooks (such as locally defined partials or other
    objects) don't have globally accessible python names. In such cases, we create
    a "shim" python_name of the form:

    `__npe1shim__.<hook_python_name>_<index>`

    The implication is that the hook should be imported, called, and indexed to return
    the corresponding item in the hook results.

    Parameters
    ----------
    shim_name : str
        A string in the form `__npe1shim__.<hook_python_name>_<index>`

    Returns
    -------
    Any
        The <index>th object returned from the callable <hook_python_name>.

    Raises
    ------
    IndexError
        If len(<hook_python_name>()) <= <index>
    """

    assert shim_name.startswith(SHIM_NAME_PREFIX), f"Invalid shim name: {shim_name}"
    python_name, idx = shim_name[13:].rsplit("_", maxsplit=1)  # TODO, make a function
    index = int(idx)

    hook = import_python_name(python_name)
    result = hook()
    if isinstance(result, dict):
        # things like sample_data hookspec return a dict, in which case we want the
        # "idxth" item in the dict (assumes ordered dict, which is safe now)
        result = list(result.values())
    if not isinstance(result, list):
        result = [result]  # pragma: no cover

    try:
        out = result[index]
    except IndexError as e:  # pragma: no cover
        raise IndexError(f"invalid npe1 shim index {index} for hook {hook}") from e

    if "dock_widget" in python_name and isinstance(out, tuple):
        return out[0]
    if "sample_data" in python_name and isinstance(out, dict):
        # this was a nested sample data
        return out.get("data")

    return out


def import_python_name(python_name: Union[PythonName, str]) -> Any:
    from importlib import import_module

    from . import _validators

    if python_name.startswith(SHIM_NAME_PREFIX):
        return _import_npe1_shim(python_name)

    _validators.python_name(python_name)  # shows the best error message
    match = _validators.PYTHON_NAME_PATTERN.match(python_name)
    module_name, funcname = match.groups()  # type: ignore [union-attr]

    mod = import_module(module_name)
    return getattr(mod, funcname)


def deep_update(dct: dict, merge_dct: dict, copy=True) -> dict:
    """Merge possibly nested dicts"""
    from copy import deepcopy

    _dct = deepcopy(dct) if copy else dct
    for k, v in merge_dct.items():
        if k in _dct and isinstance(dct[k], dict) and isinstance(v, dict):
            deep_update(_dct[k], v, copy=False)
        elif isinstance(v, list):
            if k not in _dct:
                _dct[k] = []
            _dct[k].extend(v)
        else:
            _dct[k] = v
    return _dct


def merge_manifests(manifests: Sequence[PluginManifest]):
    from npe2.manifest.schema import PluginManifest

    if not manifests:
        raise ValueError("Cannot merge empty sequence of manifests")
    if len(manifests) == 1:
        return manifests[0]

    assert len({mf.name for mf in manifests}) == 1, "All manifests must have same name"
    assert (
        len({mf.package_version for mf in manifests}) == 1
    ), "All manifests must have same version"
    assert (
        len({mf.display_name for mf in manifests}) == 1
    ), "All manifests must have same display_name"

    mf0 = manifests[0]
    info = mf0.dict(exclude={"contributions"}, exclude_unset=True)
    info["contributions"] = merge_contributions([m.contributions for m in manifests])
    return PluginManifest(**info)


def merge_contributions(contribs: Sequence[Optional[ContributionPoints]]) -> dict:
    _contribs = [c for c in contribs if c and c.dict(exclude_unset=True)]
    if not _contribs:
        return {}  # pragma: no cover

    out = _contribs[0].dict(exclude_unset=True)
    if len(_contribs) > 1:
        for n, ctrb in enumerate(_contribs[1:]):
            c = ctrb.dict(exclude_unset=True)
            for cmd in c.get("commands", ()):
                cmd["id"] = cmd["id"] + f"_{n + 2}"
            for val in c.values():
                if isinstance(val, list):
                    for item in val:
                        if "command" in item:
                            item["command"] = item["command"] + f"_{n + 2}"
            out = deep_update(out, c)
    return out


def get_pypi_url(
    name: str, version: Optional[str] = None, packagetype: Optional[str] = None
) -> str:
    """Get URL for a package on PyPI.

    Parameters
    ----------
    name : str
        package name
    version : str, optional
        package version, by default, latest version.
    packagetype : str, optional
        one of 'sdist', 'bdist_wheel', by default 'bdist_wheel' will be tried first,
        then 'sdist'

    Returns
    -------
    str
        URL to download the package.

    Raises
    ------
    ValueError
        If packagetype is not one of 'sdist', 'bdist_wheel', or if version is specified
        and does not match any available version.
    KeyError
        If packagetype is specified and no package of that type is available.
    """
    if packagetype not in {"sdist", "bdist_wheel", None}:
        raise ValueError(
            f"Invalid packagetype: {packagetype}, must be one of sdist, bdist_wheel"
        )

    with urlopen(f"https://pypi.org/pypi/{name}/json") as f:
        data = json.load(f)

    if version:
        version = version.lstrip("v")
        if version not in data["releases"]:
            raise ValueError(f"{name} does not have version {version}")
        _releases: List[dict] = data["releases"][version]
    else:
        _releases = data["urls"]

    releases = {d.get("packagetype"): d for d in _releases}
    if packagetype:
        if packagetype not in releases:
            version = version or "latest"
            raise KeyError('No {packagetype} releases found for version "{version}"')
        return releases[packagetype]["url"]
    return (releases.get("bdist_wheel") or releases["sdist"])["url"]


@contextmanager
def tmp_pip_install(
    package: str,
    version: Optional[str] = None,
    stdout: _FILE = None,
    extra_packages: Sequence[str] = (),
):
    """Context in which a pip specifier is installed and added to sys.path.

    Parameters
    ----------
    package : str
        pypi package name
    version : str, optional
        optional package version, by default, latest version.
    stdout : subprocess._FILE
        stdout for pip install, by default DEVNULL
    """
    with tempfile.TemporaryDirectory() as td:
        pkg = f"{package}=={version}" if version else package
        cmd = ["pip", "install", "--target", td, pkg] + list(extra_packages)
        run(cmd, check=True, stdout=stdout)
        sys.path.insert(0, td)
        yield td


@contextmanager
def _tmp_pypi_wheel_download(
    name: str, version: Optional[str] = None
) -> Iterator[Path]:
    url = get_pypi_url(name, version=version, packagetype="bdist_wheel")
    logger.debug(f"downloading wheel for {name} {version or ''}")
    with tempfile.TemporaryDirectory() as td, urlopen(url) as f:
        with ZipFile(BytesIO(f.read())) as zf:
            zf.extractall(td)
            yield Path(td)


def fetch_manifest(package: str, version: Optional[str] = None) -> PluginManifest:
    """Fetch a manifest for a pip specifier (package name, possibly with version).

    Parameters
    ----------
    package : str
        package name
    version : str, optional
        package version, by default, latest version.

    Returns
    -------
    PluginManifest
        Plugin manifest for package `specifier`.
    """
    from importlib.metadata import PathDistribution

    from npe2 import PluginManifest
    from npe2.manifest import PackageMetadata

    is_npe1 = False

    # first just grab the wheel from pypi with no dependencies
    with _tmp_pypi_wheel_download(package, version) as td:
        # create a PathDistribution from the dist-info directory in the wheel
        dist = PathDistribution(next(Path(td).glob("*.dist-info")))

        for ep in dist.entry_points:
            # if we find an npe2 entry point, we can just use
            # PathDistribution.locate_file to get the file.
            if ep.group == "napari.manifest":
                logger.debug("pypi wheel has npe2 entry point.")
                mf_file = dist.locate_file(Path(ep.module) / ep.attr)
                mf = PluginManifest.from_file(str(mf_file))
                # manually add the package metadata from our distribution object.
                mf.package_metadata = PackageMetadata.from_dist_metadata(dist.metadata)
                return mf
            elif ep.group == "napari.plugin":
                is_npe1 = True

    if not is_npe1:
        raise ValueError(f"{package} had no napari entry points.")

    logger.debug("falling back to npe1")
    return fetch_npe1_manifest(package, version=version)


@lru_cache
def get_all_plugins() -> Dict[str, str]:
    with urlopen("https://api.napari-hub.org/plugins") as r:
        return json.load(r)


@lru_cache
def get_plugin_info(plugin: str):
    with urlopen(f"https://api.napari-hub.org/plugins/{plugin}") as r:
        return json.load(r)


def _try_load_contributions(mf):
    from npe2.manifest._npe1_adapter import NPE1Adapter

    if not isinstance(mf, NPE1Adapter):
        return True

    mf._is_loaded = False
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "error",
                message="Error importing contributions",
                category=UserWarning,
            )
            mf._load_contributions(save=False)
            return True
    except Exception:
        return False


def fetch_npe1_manifest(package: str, version: Optional[str] = None) -> PluginManifest:
    from npe2.manifest.schema import PluginManifest

    # create an isolated env in which to install npe1 plugin
    with IsolatedEnvBuilder() as env:
        # install the package
        env.install([f"{package}=={version}" if version else package])

        # temporarily add env site packages to path
        prefixes = [getattr(env, "path")]  # noqa
        if not (site_pkgs := site.getsitepackages(prefixes=prefixes)):
            raise ValueError("No site-packages found")
        sys.path.insert(0, site_pkgs[0])

        try:
            mf = PluginManifest.from_distribution(package)

            if not _try_load_contributions(mf):
                # if loading contributions fails, it can very often be fixed
                # by installing `napari[all]` into the environment
                env.install(["napari[all]"])
                # force reloading of some modules
                sys.modules.pop("qtpy", None)
                if not _try_load_contributions(mf):
                    raise ValueError(
                        f"Unable to load contributions for npe1 plugin {package}"
                    )
            return mf
        finally:
            # cleanup sys.path
            sys.path.pop(0)


if __name__ == "__main__":
    mf = fetch_npe1_manifest("napari-clusters-plotter")
    print(mf.yaml())
