from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("npe2")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"


from ._dynamic_plugin import DynamicPlugin
from ._inspection._fetch import fetch_manifest, get_manifest_from_wheel
from ._plugin_manager import PluginContext, PluginManager
from .io_utils import read, read_get_reader, write, write_get_writer
from .manifest import PackageMetadata, PluginManifest

__all__ = [
    "DynamicPlugin",
    "PackageMetadata",
    "PluginContext",
    "PluginManager",
    "PluginManifest",
    "__version__",
    "fetch_manifest",
    "get_manifest_from_wheel",
    "read",
    "read_get_reader",
    "write",
    "write_get_writer",
]
