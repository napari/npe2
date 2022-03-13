import logging

from .._from_npe1 import manifest_from_npe1
from .package_metadata import PackageMetadata
from .schema import PluginManifest, discovery_blocked

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


logger = logging.getLogger(__name__)


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

        with discovery_blocked():
            mf = manifest_from_npe1(self._dist, shim=True)
            self.contributions = mf.contributions
            logger.debug("%r npe1 shim imported", self.name)

        self._is_loaded = True
