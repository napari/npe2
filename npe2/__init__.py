try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._dynamic_plugin import DynamicPlugin
from ._plugin_manager import PluginContext, PluginManager
from .io_utils import read, read_get_reader, write, write_get_writer
from .manifest import PackageMetadata, PluginManifest

__all__ = [
    "DynamicPlugin",
    "PluginManifest",
    "PluginManager",
    "PluginContext",
    "PackageMetadata",
    "write",
    "read",
    "read_get_reader",
    "write",
    "write_get_writer",
]
