from pydantic import BaseModel, Field

from ._commands import CommandContribution
from ._configuration import ConfigurationContribution, _ConfigurationKey
from ._keybindings import KeyBindingContribution
from ._menus import MenuItem
from ._readers import ReaderContribution
from ._sample_data import SampleDataContribution, SampleDataGenerator, SampleDataURI
from ._submenu import SubmenuContribution
from ._themes import ThemeContribution
from ._widgets import WidgetContribution
from ._writers import WriterContribution

__all__ = [
    "CommandContribution",
    "ContributionPoints",
    "KeyBindingContribution",
    "MenuItem",
    "ReaderContribution",
    "SampleDataContribution",
    "SampleDataGenerator",
    "SampleDataURI",
    "SubmenuContribution",
    "ThemeContribution",
    "WidgetContribution",
    "WriterContribution",
]


class ContributionPoints(BaseModel):
    commands: list[CommandContribution] | None = None
    readers: list[ReaderContribution] | None = None
    writers: list[WriterContribution] | None = None
    widgets: list[WidgetContribution] | None = None
    sample_data: list[SampleDataContribution] | None = None
    themes: list[ThemeContribution] | None = None
    menus: dict[str, list[MenuItem]] = Field(
        default_factory=dict,
        description="Add menu items to existing napari menus."
        "A menu item can be a command, such as open a widget, or a submenu."
        "Using menu items, nested hierarchies can be created within napari menus."
        "This allows you to organize your plugin's contributions within"
        "napari's menu structure.",
    )
    submenus: list[SubmenuContribution] | None = None
    keybindings: list[KeyBindingContribution] | None = Field(None, hide_docs=True)

    configurations: dict[_ConfigurationKey, ConfigurationContribution] = Field(
        default_factory=dict,
        description="Configuration options for this plugin, keyed by a configuration "
        "key. A plugin can contribute multiple categories of settings by declaring "
        "multiple entries here; each shows up as its own submenu in the Settings "
        "editor, headed by that entry's `title`. Each configuration key must be a "
        "valid, non-reserved Python identifier that does not begin with an "
        "underscore, and must be unique within the manifest, since it is used "
        "verbatim as the attribute name for that setting's category on the generated "
        "settings model (e.g. `get_plugin_settings('plugin-name').<configuration-key>"
        ".<property-key>`).",
    )
