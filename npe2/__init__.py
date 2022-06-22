try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._dynamic_plugin import DynamicPlugin
from ._fetch import fetch_manifest
from ._plugin_manager import PluginContext, PluginManager
from .io_utils import read, read_get_reader, write, write_get_writer
from .manifest import PackageMetadata, PluginManifest

__all__ = [
    "DynamicPlugin",
    "fetch_manifest",
    "PackageMetadata",
    "PluginContext",
    "PluginManager",
    "PluginManifest",
    "read_get_reader",
    "read",
    "write_get_writer",
    "write",
]
