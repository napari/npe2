try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._command_registry import execute_command, register_command, unregister_command
from ._plugin_manager import PluginManager
from .manifest import PluginManifest

__all__ = [
    "execute_command",
    "PluginManifest",
    "PluginManager",
    "register_command",
    "unregister_command",
]
