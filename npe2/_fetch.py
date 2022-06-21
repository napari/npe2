from __future__ import annotations

import json
import site
import sys
import tempfile
import warnings
from contextlib import contextmanager
from functools import lru_cache
from importlib import metadata
from io import BytesIO
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional
from urllib.request import urlopen
from zipfile import ZipFile

from build.env import IsolatedEnvBuilder

if TYPE_CHECKING:
    import build.env

    from npe2.manifest.schema import PluginManifest

logger = getLogger(__name__)


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
            raise KeyError(f'No {packagetype} releases found for version "{version}"')
        return releases[packagetype]["url"]
    return (releases.get("bdist_wheel") or releases["sdist"])["url"]


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
    version : Optional[str]
        package version, by default, latest version.

    Returns
    -------
    PluginManifest
        Plugin manifest for package `specifier`.
    """

    from npe2 import PluginManifest
    from npe2.manifest import PackageMetadata

    is_npe1 = False

    # first just grab the wheel from pypi with no dependencies
    try:
        with _tmp_pypi_wheel_download(package, version) as td:
            # create a PathDistribution from the dist-info directory in the wheel
            dist = metadata.PathDistribution(next(Path(td).glob("*.dist-info")))

            for ep in dist.entry_points:
                # if we find an npe2 entry point, we can just use
                # PathDistribution.locate_file to get the file.
                if ep.group == "napari.manifest":
                    logger.debug("pypi wheel has npe2 entry point.")
                    mf_file = dist.locate_file(Path(ep.module) / ep.attr)
                    mf = PluginManifest.from_file(str(mf_file))
                    # manually add the package metadata from our distribution object.
                    mf.package_metadata = PackageMetadata.from_dist_metadata(
                        dist.metadata
                    )
                    return mf
                elif ep.group == "napari.plugin":
                    is_npe1 = True
    except KeyError as e:
        if "No bdist_wheel releases found" not in str(e):
            raise
        logger.debug("falling back to npe1")
        is_npe1 = True

    if not is_npe1:
        raise ValueError(f"{package} had no napari entry points.")

    logger.debug("falling back to npe1")
    return _fetch_npe1_manifest(package, version=version)


@contextmanager
def isolated_plugin_env(
    package: str,
    version: Optional[str] = None,
    validate_npe1_imports: bool = True,
    install_napari_if_necessary: bool = True,
) -> Iterator[build.env.IsolatedEnv]:
    """Isolated env context with a plugin installed.

    The site-packages folder of the env is added to sys.path within the context.

    Parameters
    ----------
    package : str
        package name
    version : Optional[str]
        package version, by default, latest version.
    validate_npe1_imports: bool
        Whether to try to import an npe1 plugin's entry points. by default True.
    install_napari_if_necessary: bool
        If `validate_npe1_imports` is True, whether to install napari if the import
        fails.  (It's not uncommon for plugins to fail to specify napari as a
        dependency.  Othertimes, they simply need a qt backend.).  by default True.

    Yields
    ------
    build.env.IsolatedEnv
        env object that has an `install` method.
    """
    with IsolatedEnvBuilder() as env:
        # install the package
        pkg = f"{package}=={version}" if version else package
        logger.debug(f"installing {pkg} into virtual env")
        env.install([pkg])

        # temporarily add env site packages to path
        prefixes = [getattr(env, "path")]  # noqa
        if not (site_pkgs := site.getsitepackages(prefixes=prefixes)):
            raise ValueError("No site-packages found")
        sys.path.insert(0, site_pkgs[0])
        try:
            if validate_npe1_imports:
                dist = metadata.distribution(package)

                npe1_eps: List[metadata.EntryPoint] = []
                npe2_ep: Optional[metadata.EntryPoint] = None
                for ep in dist.entry_points:
                    if ep.group == "napari.plugin":
                        npe1_eps.append(ep)
                    elif ep.group == "napari.manifest":
                        npe2_ep = ep

                if npe2_ep is None:
                    for ep in npe1_eps:
                        try:
                            ep.load()
                        except ImportError:
                            # if loading contributions fails, it can very often be fixed
                            # by installing `napari[all]` into the environment
                            if install_napari_if_necessary:
                                env.install(["napari[all]"])
                                # force reloading of qtpy
                                sys.modules.pop("qtpy", None)
                                ep.load()
                            else:
                                raise
            yield env
        finally:
            # cleanup sys.path
            sys.path.pop(0)


def _fetch_npe1_manifest(package: str, version: Optional[str] = None) -> PluginManifest:
    """Fetch manifest for npe1 plugin in an isolated environment."""
    from npe2.manifest._npe1_adapter import NPE1Adapter
    from npe2.manifest.schema import PluginManifest

    # create an isolated env in which to install npe1 plugin
    with isolated_plugin_env(package, version):
        mf = PluginManifest.from_distribution(package)
        if isinstance(mf, NPE1Adapter):
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "error", message="Error importing contributions"
                )
                mf._load_contributions(save=False)
        return mf


@lru_cache
def get_all_plugins() -> Dict[str, str]:
    """Return {name: latest_version} for all plugins on the hub."""
    with urlopen("https://api.napari-hub.org/plugins") as r:
        return json.load(r)


@lru_cache
def get_plugin_info(plugin: str) -> Dict[str, Any]:
    """Return hub information for a specific plugin."""
    with urlopen(f"https://api.napari-hub.org/plugins/{plugin}") as r:
        return json.load(r)
