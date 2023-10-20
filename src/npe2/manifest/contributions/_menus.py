from typing import Optional, Union

from npe2._pydantic_compat import BaseModel, Field
from npe2.manifest.utils import Executable


# user provides this
class _MenuItem(BaseModel):
    """Generic menu item contribution."""

    when: Optional[str] = Field(
        description="Condition which must be true to *show* this item in the menu. "
        "Note that ``when`` clauses apply to menus and ``enablement`` clauses to "
        "commands. The ``enablement`` applies to all menus and even keybindings while "
        "the ``when`` only applies to a single menu."
    )
    # TODO: declare groups for every menu exposed by napari:
    # e.g. `2_compare`, `4_search`, `6_cutcopypaste`
    group: Optional[str] = Field(
        description="The `group` property defines sorting and grouping of menu items. "
        "The `'navigation'` group is special: it will always be sorted to the "
        "top/beginning of a menu. By default, the order *inside* a group depends on "
        "the `title`. The group-local order of a menu item can be specified by "
        "appending @<int> to the group identifier: e.g. `group: 'myGroup@2'`."
    )


class Submenu(_MenuItem):
    """Contributes a submenu placement in a menu."""

    submenu: str = Field(
        ...,
        description="Identifier of the submenu to display in this item."
        "The submenu must be declared in the 'submenus' -section",
    )
    # if submenu doesn't exist, you get:
    # Menu item references a submenu ...` which is not defined in the 'submenus' section


class MenuCommand(_MenuItem, Executable):
    """Contributes a command in a menu."""

    command: str = Field(
        ...,
        description="Identifier of the command to execute. "
        "The command must be declared in the 'commands' section",
    )
    # if command doesn't exist, you get:
    # "Menu item references a command `...` which is not defined in the
    # 'commands' section."
    alt: Optional[str] = Field(
        description="Identifier of an alternative command to execute. "
        "It will be shown and invoked when pressing Alt while opening a menu."
        "The command must be declared in the 'commands' section"
    )


MenuItem = Union[MenuCommand, Submenu]
