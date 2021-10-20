try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._plugin_manager import PluginContext, PluginManager
from .manifest import PluginManifest

__all__ = ["PluginManifest", "PluginManager", "PluginContext"]
