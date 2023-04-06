import contextlib
import logging
import os
import site
import warnings
from importlib import metadata
from pathlib import Path
from shutil import rmtree
from typing import List, Sequence

from appdirs import user_cache_dir

from npe2._inspection._from_npe1 import manifest_from_npe1
from npe2.manifest import PackageMetadata

from .schema import PluginManifest, discovery_blocked

logger = logging.getLogger(__name__)
ADAPTER_CACHE = Path(user_cache_dir("napari", "napari")) / "npe2" / "adapter_manifests"
NPE2_NOCACHE = "NPE2_NOCACHE"


def clear_cache(names: Sequence[str] = ()) -> List[Path]:
    """Clear cached NPE1Adapter manifests.

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
    if ADAPTER_CACHE.exists():
        if names:
            for f in ADAPTER_CACHE.glob("*.yaml"):
                if any(f.name.startswith(f"{n}_") for n in names):
                    f.unlink()
                    _cleared.append(f)
        else:
            _cleared = list(ADAPTER_CACHE.iterdir())
            rmtree(ADAPTER_CACHE)
    return _cleared


class NPE1Adapter(PluginManifest):
    """PluginManifest subclass that acts as an adapter for 1st gen plugins.

    During plugin discovery, packages that provide a first generation
    'napari.plugin' entry_point (but do *not* provide a second generation
    'napari.manifest' entrypoint) will be stored as `NPE1Adapter` manifests
    in the `PluginManager._npe1_adapters` list.

    This class is instantiated with only a distribution object, but lacks
    contributions at construction time.  When `self.contributions` is accesses for the
    first time, `_load_contributions` is called triggering and import and indexing of
    all plugin modules using the same logic as `npe2 convert`.  After import, the
    discovered contributions are cached in a manifest for use in future sessions.
    (The cache can be cleared using `npe2 cache --clear [plugin-name]`).



    Parameters
    ----------
    dist : metadata.Distribution
        A Distribution object for a package installed in the environment. (Minimally,
        the distribution object must implement the `metadata` and `entry_points`
        attributes.).  It will be passed to `manifest_from_npe1`
    """

    _is_loaded: bool = False
    _dist: metadata.Distribution

    def __init__(self, dist: metadata.Distribution):
        """_summary_"""
        meta = PackageMetadata.from_dist_metadata(dist.metadata)
        super().__init__(
            name=dist.metadata["Name"], package_metadata=meta, npe1_shim=True
        )
        self._dist = dist

    def __getattribute__(self, __name: str):
        if __name == "contributions":
            self._load_contributions()
        return super().__getattribute__(__name)

    def _load_contributions(self, save=True) -> None:
        """import and inspect package contributions."""
        if self._is_loaded:
            return
        self._is_loaded = True  # if we fail once, we still don't try again.
        if self._cache_path().exists() and not os.getenv(NPE2_NOCACHE):
            mf = PluginManifest.from_file(self._cache_path())
            self.contributions = mf.contributions
            logger.debug("%r npe1 adapter loaded from cache", self.name)
            return

        with discovery_blocked():
            try:
                mf = manifest_from_npe1(self._dist, adapter=True)
            except Exception as e:
                warnings.warn(
                    "Error importing contributions for first-generation "
                    f"napari plugin {self.name!r}: {e}",
                    stacklevel=2,
                )
                return

            self.contributions = mf.contributions
            logger.debug("%r npe1 adapter imported", self.name)

        if save and not _is_editable_install(self._dist):
            with contextlib.suppress(OSError):
                self._save_to_cache()

    def _save_to_cache(self):
        cache_path = self._cache_path()
        cache_path.parent.mkdir(exist_ok=True, parents=True)
        cache_path.write_text(self.yaml())

    def _cache_path(self) -> Path:
        """Return cache path for manifest corresponding to distribution."""
        return _cached_adapter_path(self.name, self.package_version or "")

    def _serialized_data(self, **kwargs):
        if not self._is_loaded:  # pragma: no cover
            self._load_contributions(save=False)
        return super()._serialized_data(**kwargs)


def _cached_adapter_path(name: str, version: str) -> Path:
    """Return cache path for manifest corresponding to distribution."""
    return ADAPTER_CACHE / f"{name}_{version}.yaml"


def _is_editable_install(dist: metadata.Distribution) -> bool:
    """Return True if dist is installed as editable.

    i.e: if the package isn't in site-packages or user site-packages.
    """
    root = str(dist.locate_file(""))
    installed_paths = [*site.getsitepackages(), site.getusersitepackages()]
    return all(loc not in root for loc in installed_paths)
