import logging
import warnings

from .._from_npe1 import manifest_from_npe1
from .package_metadata import PackageMetadata
from .schema import PluginManifest, discovery_blocked

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


logger = logging.getLogger(__name__)


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
        super().__init__(name=dist.metadata["Name"], package_metadata=meta)
        self._dist = dist

    def __getattribute__(self, __name: str):
        if __name == "contributions" and not self._is_loaded:
            self._load_contributions()
        return super().__getattribute__(__name)

    def _load_contributions(self) -> None:
        """import and inspect package contributions."""

        with discovery_blocked():
            self._is_loaded = True  # if we fail once, we still don't try again.
            try:
                mf = manifest_from_npe1(self._dist, adapter=True)
            except Exception as e:
                warnings.warn(
                    "Error importing contributions for first-generation "
                    f"napari plugin {self.name!r}: {e}"
                )
                return

            self.contributions = mf.contributions
            logger.debug("%r npe1 adapter imported", self.name)
