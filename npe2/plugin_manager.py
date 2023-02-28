# mypy: disable-error-code=empty-body
"""Convenience module to access methods on the global PluginManager singleton."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Iterator, List, NewType, Optional, Sequence, Tuple, Union

    from npe2 import PluginManifest
    from npe2._plugin_manager import InclusionSet, PluginContext
    from npe2.manifest import contributions

    from ._plugin_manager import PluginManager

    PluginName = NewType("PluginName", str)


def instance() -> PluginManager:
    """Return global PluginManager singleton instance."""
    from ._plugin_manager import PluginManager

    return PluginManager.instance()


def discover(paths: Sequence[str] = (), clear=False, include_npe1=False) -> None:
    """Discover and index plugin manifests in the environment."""


def dict(
    self,
    *,
    include: Optional[InclusionSet] = None,
    exclude: Optional[InclusionSet] = None,
) -> Dict[str, Any]:
    """Return a dictionary with the state of the plugin manager."""


def index_npe1_adapters() -> None:
    """Import and index any/all npe1 adapters."""


def register(manifest: PluginManifest, warn_disabled=True) -> None:
    """Register a plugin manifest"""


def unregister(key: PluginName) -> None:
    """Unregister plugin named `key`."""


def activate(key: PluginName) -> PluginContext:
    """Activate plugin with `key`."""


def get_context(plugin_name: PluginName) -> PluginContext:
    """Return PluginContext for plugin_name"""


def deactivate(plugin_name: PluginName) -> None:
    """Deactivate `plugin_name`"""


def enable(plugin_name: PluginName) -> None:
    """Enable a plugin (which mostly means just `un-disable` it."""


def disable(plugin_name: PluginName) -> None:
    """Disable a plugin"""


def is_disabled(plugin_name: str) -> bool:
    """Return `True` if plugin_name is disabled."""


def get_manifest(plugin_name: str) -> PluginManifest:
    """Get manifest for `plugin_name`"""


def iter_manifests(disabled: Optional[bool] = None) -> Iterator[PluginManifest]:
    """Iterate through registered manifests."""


def get_command(command_id: str) -> contributions.CommandContribution:
    """Retrieve CommandContribution for `command_id`"""


def get_submenu(submenu_id: str) -> contributions.SubmenuContribution:
    """Get SubmenuContribution for `submenu_id`."""


def iter_menu(menu_key: str, disabled=False) -> Iterator[contributions.MenuItem]:
    """Iterate over `MenuItems` in menu with id `menu_key`."""


def menus(disabled=False) -> Dict[str, List[contributions.MenuItem]]:
    """Return all registered menu_key -> List[MenuItems]."""


def iter_themes() -> Iterator[contributions.ThemeContribution]:
    """Iterate over discovered/enuabled `ThemeContributions`."""


def iter_compatible_readers(
    path: Union[PathLike, Sequence[str]]
) -> Iterator[contributions.ReaderContribution]:
    """Iterate over ReaderContributions compatible with `path`."""


def iter_compatible_writers(
    layer_types: Sequence[str],
) -> Iterator[contributions.WriterContribution]:
    """Iterate over compatible WriterContributions given a sequence of layer_types."""


def iter_widgets() -> Iterator[contributions.WidgetContribution]:
    """Iterate over discovered WidgetContributions."""


def iter_sample_data() -> (
    Iterator[Tuple[PluginName, List[contributions.SampleDataContribution]]]
):
    """Iterates over (plugin_name, [sample_contribs])."""


def get_writer(
    path: str, layer_types: Sequence[str], plugin_name: Optional[str] = None
) -> Tuple[Optional[contributions.WriterContribution], str]:
    """Get Writer contribution appropriate for `path`, and `layer_types`."""


def _populate_module():
    """Convert all functions in this module into global plugin manager methods."""
    import functools
    import sys

    from ._plugin_manager import PluginManager

    _module = sys.modules[__name__]
    for key in dir(_module):
        if key.startswith(("_", "instance")) or not hasattr(PluginManager, key):
            continue

        @functools.wraps(getattr(_module, key))
        def _f(*args, _key=key, **kwargs):
            return getattr(instance(), _key)(*args, **kwargs)

        setattr(_module, key, _f)


_populate_module()
del _populate_module, TYPE_CHECKING, annotations
