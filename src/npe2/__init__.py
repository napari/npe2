from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("npe2")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from typing import TYPE_CHECKING, Any

from ._dynamic_plugin import DynamicPlugin
from ._plugin_manager import PluginContext, PluginManager
from .io_utils import read, read_get_reader, write, write_get_writer
from .manifest import PackageMetadata, PluginManifest

if TYPE_CHECKING:
    from ._inspection._fetch import fetch_manifest, get_manifest_from_wheel

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


def __getattr__(name: str) -> Any:
    """Lazily (PEP562) import inspection utilities."""
    if name in ("fetch_manifest", "get_manifest_from_wheel"):
        from ._inspection import _fetch

        val = getattr(_fetch, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
