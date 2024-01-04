from __future__ import annotations

import io
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from functools import lru_cache
from importlib import metadata
from logging import getLogger
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)
from unittest.mock import patch
from urllib import error, parse, request
from zipfile import ZipFile

from npe2.manifest import PackageMetadata

if TYPE_CHECKING:
    from npe2.manifest import PluginManifest


logger = getLogger(__name__)

NPE1_ENTRY_POINT = "napari.plugin"
NPE2_ENTRY_POINT = "napari.manifest"
__all__ = [
    "fetch_manifest",
    "get_pypi_url",
    "get_hub_plugin",
    "get_pypi_plugins",
]


def _manifest_from_npe2_dist(
    dist: metadata.PathDistribution, ep: metadata.EntryPoint
) -> PluginManifest:
    """Extract plugin manifest from a distribution with an npe2 entry point."""
    from npe2.manifest import PluginManifest

    logger.debug("pypi wheel has npe2 entry point.")

    # python 3.8 fallbacks
    match = ep.pattern.match(ep.value)
    assert match
    module: str = match.groupdict()["module"]
    attr: str = match.groupdict()["attr"]

    mf_file = Path(dist.locate_file(Path(module.replace(".", os.sep)) / attr))
    if not mf_file.exists():
        raise ValueError(  # pragma: no cover
            f"manifest {mf_file.name!r} does not exist in distribution "
            f"for {dist.metadata['Name']}"
        )

    mf = PluginManifest.from_file(str(mf_file))
    # manually add the package metadata from our distribution object.
    mf.package_metadata = PackageMetadata.from_dist_metadata(dist.metadata)
    return mf


def _manifest_from_npe1_dist(dist: metadata.PathDistribution) -> PluginManifest:
    """Extract plugin manifest from a distribution with an npe1 entry point."""
    from npe2.manifest import PluginManifest
    from npe2.manifest.utils import merge_contributions

    from . import find_npe1_module_contributions

    name = dist.metadata["Name"]
    contribs = []
    for ep in dist.entry_points:
        if ep.group == NPE1_ENTRY_POINT and (match := ep.pattern.match(ep.value)):
            module = match.group("module")
            contribs.append(find_npe1_module_contributions(dist, module))

    mf = PluginManifest(
        name=name, contributions=merge_contributions(contribs), npe1_shim=True
    )
    mf.package_metadata = PackageMetadata.from_dist_metadata(dist.metadata)
    return mf


def _manifest_from_extracted_wheel(wheel_dir: Path) -> PluginManifest:
    """Return plugin manifest from an extracted wheel."""
    # create a PathDistribution from the dist-info directory in the wheel
    dist = metadata.PathDistribution(next(Path(wheel_dir).glob("*.dist-info")))

    has_npe1 = False
    for ep in dist.entry_points:
        # if we find an npe2 entry point, we can just use
        # PathDistribution.locate_file to get the file.
        if ep.group == NPE2_ENTRY_POINT:
            return _manifest_from_npe2_dist(dist, ep)
        elif ep.group == NPE1_ENTRY_POINT:
            has_npe1 = True  # pragma: no cover
    if has_npe1:
        return _manifest_from_npe1_dist(dist)

    raise ValueError("No npe2 or npe1 entry point found in wheel")  # pragma: no cover


@contextmanager
def _guard_cwd() -> Iterator[None]:
    """Protect current working directory from changes."""
    current = os.getcwd()
    try:
        yield
    finally:
        os.chdir(current)


def _build_wheel(src: Union[str, Path]) -> Path:
    """Build a wheel from a source directory and extract it into dest."""
    from build.__main__ import build_package

    dest = Path(src) / "extracted_wheel"

    class _QuietPopen(subprocess.Popen):
        """Silence all the noise from build."""

        def __init__(self, *args, **kwargs):
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
            super().__init__(*args, **kwargs)

    with patch("subprocess.Popen", _QuietPopen), _guard_cwd():
        dist = Path(src) / "dist"
        build_package(src, dist, ["wheel"])
        with ZipFile(next((dist).glob("*.whl"))) as zf:
            zf.extractall(dest)
    return dest


def get_manifest_from_wheel(src: str) -> PluginManifest:
    """Extract a manifest from a .whl file."""
    with tempfile.TemporaryDirectory() as td:
        with ZipFile(src) as zf:
            zf.extractall(td)
            return _manifest_from_extracted_wheel(Path(td))


def _build_src_and_extract_manifest(src_dir: Union[str, Path]) -> PluginManifest:
    """Build a wheel from a source directory and extract the manifest."""
    return _manifest_from_extracted_wheel(_build_wheel(src_dir))


def _get_manifest_from_zip_url(url: str) -> PluginManifest:
    """Extract a manifest from a remote source directory zip file.

    Examples
    --------
    $ npe2 fetch https://github.com/org/project/archive/refs/heads/master.zip
    """
    with _tmp_zip_download(url) as zip_path:
        src_dir = next(Path(zip_path).iterdir())  # find first directory
        return _build_src_and_extract_manifest(src_dir)


def _get_manifest_from_wheel_url(url: str) -> PluginManifest:
    """Extract a manifest from a remote wheel file.

    Examples
    --------
    $ npe2 fetch https://files.pythonhosted.org/packages/b0/93/a00a1ee154d5ce3540dd5ae081dc53fcfa7498f34ba68a7345ac027a4f96/pycudadecon-0.3.0-py3-none-any.whl
    """
    with _tmp_zip_download(url) as wheel_dir:
        return _manifest_from_extracted_wheel(wheel_dir)


def _get_manifest_from_targz_url(url: str) -> PluginManifest:
    """Extract a manifest from a remote source directory tar.gz file.

    Examples
    --------
    $ npe2 fetch https://files.pythonhosted.org/packages/4a/84/de031ba465f183c319cb37633c49dfebd57f1ff42bc9744db3f80f7f4093/pycudadecon-0.3.0.tar.gz
    """
    with _tmp_targz_download(url) as targz_path:
        src_dir = next(Path(targz_path).iterdir())  # find first directory
        return _build_src_and_extract_manifest(src_dir)


def _get_manifest_from_git_url(url: str) -> PluginManifest:
    """Extract a manifest from a remote git repository.

    Examples
    --------
    $ npe2 fetch https://github.com/tlambert03/napari-dv
    $ npe2 fetch https://github.com/tlambert03/napari-dv.git
    $ npe2 fetch git+https://github.com/tlambert03/napari-dv.git
    """
    if url.startswith("git+"):
        url = url[4:]

    branch = ""
    if "@" in url:
        url, branch = url.split("@")

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "clone", url, td], stdout=subprocess.DEVNULL)
        if branch:
            subprocess.run(
                ["git", "checkout", branch], cwd=td, stdout=subprocess.DEVNULL
            )
        return _build_src_and_extract_manifest(td)


def fetch_manifest(
    package_or_url: str, version: Optional[str] = None
) -> PluginManifest:
    """Fetch a manifest for a pypi package name or URL to a wheel or source.

    Parameters
    ----------
    package_or_url : str
        package name or URL to a git repository or zip file.
    version : Optional[str]
        package version, by default, latest version.

    Returns
    -------
    PluginManifest
        Plugin manifest for package `specifier`.

    Examples
    --------
    >>> fetch_manifest("napari-dv")
    >>> fetch_manifest("napari-dv", "0.3.0")
    >>> fetch_manifest("https://github.com/tlambert03/napari-dv")
    >>> fetch_manifest("git+https://github.com/tlambert03/napari-dv.git")
    >>> fetch_manifest("https://github.com/org/project/archive/refs/heads/master.zip")
    >>> fetch_manifest("https://files.pythonhosted.org/.../package-0.3.0-py3-none-any.whl")
    >>> fetch_manifest("https://files.pythonhosted.org/.../package-0.3.0.tar.gz")
    """
    # not on PyPI check various URL forms
    if package_or_url.startswith(("http", "git+http")):
        if package_or_url.endswith(".zip"):
            return _get_manifest_from_zip_url(package_or_url)
        if package_or_url.endswith(".whl"):
            return _get_manifest_from_wheel_url(package_or_url)
        if package_or_url.endswith(".tar.gz"):
            return _get_manifest_from_targz_url(package_or_url)
        if (
            package_or_url.startswith("git+")
            or package_or_url.endswith(".git")
            or "github.com" in package_or_url
        ):
            return _get_manifest_from_git_url(package_or_url)
    else:
        try:
            with _tmp_pypi_wheel_download(package_or_url, version) as td:
                return _manifest_from_extracted_wheel(td)
        except metadata.PackageNotFoundError:
            return _manifest_from_pypi_sdist(package_or_url, version)
        except error.HTTPError:
            pass  # pragma: no cover
    raise ValueError(  # pragma: no cover
        f"Could not interpret {package_or_url!r} as a PYPI package name or URL to a "
        "wheel or source distribution/zip file."
    )


def _manifest_from_pypi_sdist(
    package: str, version: Optional[str] = None
) -> PluginManifest:
    """Extract a manifest from a source distribution on pypi."""
    with _tmp_pypi_sdist_download(package, version) as td:
        src = next(p for p in td.iterdir() if p.is_dir())
        return _build_src_and_extract_manifest(src)


@lru_cache
def _pypi_info(package: str) -> dict:
    with request.urlopen(f"https://pypi.org/pypi/{package}/json") as f:
        return json.load(f)


def get_pypi_url(
    package: str, version: Optional[str] = None, packagetype: Optional[str] = None
) -> str:
    """Get URL for a package on PyPI.

    Parameters
    ----------
    package : str
        package name
    version : str, optional
        package version, by default, latest version.
    packagetype : str, optional
        one of `'sdist'`, `'bdist_wheel'`, or `None`,
        by default `None`, which means 'bdist_wheel' will be tried first, then 'sdist'

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
        raise ValueError(  # pragma: no cover
            f"Invalid packagetype: {packagetype}, must be one of sdist, bdist_wheel"
        )

    data = _pypi_info(package)
    if version:
        version = version.lstrip("v")
        try:
            _releases: List[dict] = data["releases"][version]
        except KeyError as e:  # pragma: no cover
            raise ValueError(f"{package} does not have version {version}") from e
    else:
        _releases = data["urls"]

    releases = {d.get("packagetype"): d for d in _releases}
    if packagetype:
        if packagetype not in releases:  # pragma: no cover
            version = version or "latest"
            raise metadata.PackageNotFoundError(
                f'No {packagetype} releases found for version "{version}"'
            )
        return releases[packagetype]["url"]
    return (releases.get("bdist_wheel") or releases["sdist"])["url"]


@contextmanager
def _tmp_zip_download(url: str) -> Iterator[Path]:
    """Extract remote zip file to a temporary directory."""
    with tempfile.TemporaryDirectory() as td, request.urlopen(url) as f:
        with ZipFile(io.BytesIO(f.read())) as zf:
            zf.extractall(td)
            yield Path(td)


@contextmanager
def _tmp_targz_download(url: str) -> Iterator[Path]:
    """Extract remote tar.gz file to a temporary directory."""
    import tarfile

    with tempfile.TemporaryDirectory() as td, request.urlopen(url) as f:
        with tarfile.open(fileobj=f, mode="r:gz") as tar:
            tar.extractall(td)
            yield Path(td)


def _tmp_pypi_wheel_download(
    package: str, version: Optional[str] = None
) -> ContextManager[Path]:
    url = get_pypi_url(package, version=version, packagetype="bdist_wheel")
    logger.debug(f"downloading wheel for {package} {version or ''}")
    return _tmp_zip_download(url)


def _tmp_pypi_sdist_download(
    package: str, version: Optional[str] = None
) -> ContextManager[Path]:
    url = get_pypi_url(package, version=version, packagetype="sdist")
    logger.debug(f"downloading sdist for {package} {version or ''}")
    return _tmp_targz_download(url)


@lru_cache
def _get_packages_by_classifier(classifier: str) -> Dict[str, str]:
    """Search for packages declaring ``classifier`` on PyPI.

    Returns
    -------
    packages : List[str]
        name of all packages at pypi that declare ``classifier``
    """
    PACKAGE_NAME_PATTERN = re.compile('class="package-snippet__name">(.+)</span>')
    PACKAGE_VERSION_PATTERN = re.compile('class="package-snippet__version">(.+)</span>')

    packages = {}
    page = 1
    url = f"https://pypi.org/search/?c={parse.quote_plus(classifier)}&page="
    while True:
        try:
            with request.urlopen(f"{url}{page}") as response:
                html = response.read().decode()
            names = PACKAGE_NAME_PATTERN.findall(html)
            versions = PACKAGE_VERSION_PATTERN.findall(html)
            packages.update(dict(zip(names, versions)))
            page += 1
        except error.HTTPError:
            break

    return dict(sorted(packages.items()))


def get_pypi_plugins() -> Dict[str, str]:
    """Return {name: latest_version} for all plugins found on pypi."""
    NAPARI_CLASSIFIER = "Framework :: napari"
    return _get_packages_by_classifier(NAPARI_CLASSIFIER)


@lru_cache
def get_hub_plugin(plugin_name: str) -> Dict[str, Any]:
    """Return hub information for a specific plugin."""
    with request.urlopen(f"https://api.napari-hub.org/plugins/{plugin_name}") as r:
        return json.load(r)


def _try_fetch_and_write_manifest(args: Tuple[str, str, Path, int]):
    name, version, dest, indent = args
    FORMAT = "json"

    try:  # pragma: no cover
        mf = fetch_manifest(name, version=version)
        manifest_string = getattr(mf, FORMAT)(exclude=set(), indent=indent)

        (dest / f"{name}.{FORMAT}").write_text(manifest_string)
        print(f"✅ {name}")
    except Exception as e:
        print(f"❌ {name}")
        return name, {"version": version, "error": str(e)}


def fetch_all_manifests(dest: str = "manifests", indent: int = 2) -> None:
    """Fetch all manifests for plugins on PyPI and write to ``dest`` directory."""
    _dest = Path(dest)
    _dest.mkdir(exist_ok=True, parents=True)

    args = [
        (name, ver, _dest, indent) for name, ver in sorted(get_pypi_plugins().items())
    ]

    # use processes instead of threads, because many of the subroutines in build
    # and setuptools use `os.chdir()`, which is not thread-safe
    with ProcessPoolExecutor() as executor:
        errors = list(executor.map(_try_fetch_and_write_manifest, args))
    _errors = {tup[0]: tup[1] for tup in errors if tup}
    (_dest / "errors.json").write_text(json.dumps(_errors, indent=indent))
