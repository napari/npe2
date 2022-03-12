try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._plugin_manager import PluginContext, PluginManager
from .io_utils import read, write
from .manifest import PluginManifest
from .manifest.package_metadata import PackageMetadata

__all__ = [
    "PluginManifest",
    "PluginManager",
    "PluginContext",
    "PackageMetadata",
    "write",
    "read",
]
