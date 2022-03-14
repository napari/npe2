import logging
import os
import site
import warnings
from pathlib import Path
from shutil import rmtree
from typing import List, Sequence

from appdirs import user_cache_dir

from .._from_npe1 import manifest_from_npe1
from .package_metadata import PackageMetadata
from .schema import PluginManifest, discovery_blocked

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


logger = logging.getLogger(__name__)
SHIM_CACHE = Path(user_cache_dir("napari", "napari")) / "npe2" / "shims"
NPE2_NOCACHE = "NPE2_NOCACHE"


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
    _dist: metadata.Distribution

    def __init__(self, dist: metadata.Distribution):
        meta = PackageMetadata.from_dist_metadata(dist.metadata)
        super().__init__(name=dist.metadata["Name"], package_metadata=meta)
        self._dist = dist

    def __getattribute__(self, __name: str):
        if __name == "contributions" and not self._is_loaded:
            self._load_contributions()
        return super().__getattribute__(__name)

    def _load_contributions(self) -> None:
        """imports and inspects package using npe1 plugin manager"""

        self._is_loaded = True  # if we fail once, we still don't try again.
        if self._cache_path().exists() and not os.getenv(NPE2_NOCACHE):
            mf = PluginManifest.from_file(self._cache_path())
            self.contributions = mf.contributions
            logger.debug("%r npe1 shim loaded from cache", self.name)
            return

        with discovery_blocked():
            try:
                mf = manifest_from_npe1(self._dist, shim=True)
            except Exception as e:
                warnings.warn(
                    f"Failed to detect contributions for np1e plugin {self.name!r}: {e}"
                )
                return

            self.contributions = mf.contributions
            logger.debug("%r npe1 shim imported", self.name)

        if not _is_editable_install(self._dist):
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


def _is_editable_install(dist: metadata.Distribution) -> bool:
    """Return True if dist is installed as editable.

    i.e: if the package isn't in site-packages or user site-packages.
    """
    root = str(dist.locate_file(""))
    installed_paths = site.getsitepackages() + [site.getusersitepackages()]
    return all(loc not in root for loc in installed_paths)
