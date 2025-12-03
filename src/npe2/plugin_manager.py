# mypy: disable-error-code=empty-body
"""Convenience module to access methods on the global PluginManager singleton."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from os import PathLike
    from typing import Any, NewType

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
    include: InclusionSet | None = None,
    exclude: InclusionSet | None = None,
) -> builtins.dict[str, Any]:
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


def iter_manifests(disabled: bool | None = None) -> Iterator[PluginManifest]:
    """Iterate through registered manifests."""


def get_command(command_id: str) -> contributions.CommandContribution:
    """Retrieve CommandContribution for `command_id`"""


def get_submenu(submenu_id: str) -> contributions.SubmenuContribution:
    """Get SubmenuContribution for `submenu_id`."""


def iter_menu(menu_key: str, disabled=False) -> Iterator[contributions.MenuItem]:
    """Iterate over `MenuItems` in menu with id `menu_key`."""


def menus(disabled=False) -> builtins.dict[str, list[contributions.MenuItem]]:
    """Return all registered menu_key -> List[MenuItems]."""


def iter_themes() -> Iterator[contributions.ThemeContribution]:
    """Iterate over discovered/enuabled `ThemeContributions`."""


def iter_compatible_readers(
    path: PathLike | Sequence[str],
) -> Iterator[contributions.ReaderContribution]:
    """Iterate over ReaderContributions compatible with `path`."""


def iter_compatible_writers(
    layer_types: Sequence[str],
) -> Iterator[contributions.WriterContribution]:
    """Iterate over compatible WriterContributions given a sequence of layer_types."""


def iter_widgets() -> Iterator[contributions.WidgetContribution]:
    """Iterate over discovered WidgetContributions."""


def iter_sample_data() -> Iterator[
    tuple[PluginName, list[contributions.SampleDataContribution]]
]:
    """Iterates over (plugin_name, [sample_contribs])."""


def get_writer(
    path: str, layer_types: Sequence[str], plugin_name: str | None = None
) -> tuple[contributions.WriterContribution | None, str]:
    """Get Writer contribution appropriate for `path`, and `layer_types`."""


def get_shimmed_plugins() -> list[str]:
    """Return a list of all shimmed plugin names."""


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
