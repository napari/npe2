import logging
from pathlib import Path
from shutil import rmtree
from site import getsitepackages, getusersitepackages
from typing import List, Sequence, Union

from appdirs import user_cache_dir

from .._from_npe1 import manifest_from_npe1
from .contributions import ContributionPoints
from .schema import NPE1_ENTRY_POINT, PluginManifest, discovery_blocked
from .utils import merge_contributions

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


logger = logging.getLogger(__name__)
SHIM_CACHE = Path(user_cache_dir("napari", "napari")) / "npe2" / "shims"


def clear_cache(names: Sequence[str] = ()) -> List[Path]:
    """Clear cached npe1 shim files

    Parameters
    ----------
    names : Sequence[str], optional
        selection of plugin names to clear, by default, all will be cleared

    Returns
    -------
    List[Path]
        List of filepaths cleared
    """
    _cleared: List[Path] = []
    if SHIM_CACHE.exists():
        if names:
            for f in SHIM_CACHE.glob("*.yaml"):
                if any(f.name.startswith(f"{n}_") for n in names):
                    f.unlink()
                    _cleared.append(f)
        else:
            _cleared = list(SHIM_CACHE.iterdir())
            rmtree(SHIM_CACHE)
    return _cleared


class NPE1Shim(PluginManifest):
    _is_loaded: bool = False

    def __getattribute__(self, __name: str):
        if __name == "contributions" and not self._is_loaded:
            self._load_contributions()
        return super().__getattribute__(__name)

    def _load_contributions(self) -> None:
        """imports and inspects package using npe1 plugin manager"""

        if self._cache_path().exists():
            mf = PluginManifest.from_file(self._cache_path())
            self.contributions = mf.contributions
            self._is_loaded = True
            logger.debug("%r npe1 shim loaded from cache", self.name)
            return

        dist = metadata.distribution(self.name)
        with discovery_blocked():
            mfs = [
                manifest_from_npe1(ep.name, shim=True)
                for ep in dist.entry_points
                if ep.group == NPE1_ENTRY_POINT
            ]
            assert mfs, "No npe1 entry points found in distribution {name}"

            contribs = merge_contributions([m.contributions for m in mfs])
            self.contributions = ContributionPoints(**contribs)
            logger.debug("%r npe1 shim imported", self.name)

        self._is_loaded = True
        if not _is_editable_install(dist):
            self._save_to_cache()

    def _save_to_cache(self):
        cache_path = self._cache_path()
        cache_path.parent.mkdir(exist_ok=True, parents=True)
        cache_path.write_text(self.yaml())

    def _cache_path(self) -> Path:
        """Return cache path for manifest corresponding to distribution."""
        return _cached_shim_path(self.name, self.package_version or "")


def _cached_shim_path(name: str, version: str) -> Path:
    """Return cache path for manifest corresponding to distribution."""
    return SHIM_CACHE / f"{name}_{version}.yaml"


def _is_editable_install(dist: Union[str, metadata.Distribution]) -> bool:
    """Return True if dist or distname is installed as editable.

    i.e: if the package isn't in site-packages or user site-packages.
    """
    if isinstance(dist, str):
        dist = metadata.distribution(dist)

    root = str(dist.locate_file(""))
    installed_paths = getsitepackages() + [getusersitepackages()]
    return all(loc not in root for loc in installed_paths)
