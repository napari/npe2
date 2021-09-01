try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from .manifest import PluginManifest
from ._command_registry import (
    register_command,
    unregister_command,
    execute_command,
)
from ._plugin_manager import plugin_manager

__all__ = [
    "execute_command",
    "plugin_manager",
    "PluginManifest",
    "register_command",
    "unregister_command",
]
