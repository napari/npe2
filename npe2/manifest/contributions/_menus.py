from typing import Optional, Union

from pydantic import BaseModel, Field

from ..utils import Executable


# a list of valid napari menu locations that plugins can contribute too.
# keys provided in the plugin manifest must match these strings
napari_menus = ['/napari/layer_context',
                '/napari/layer_context/projections',
                '/napari/layer_context/convert_type',
                '/napari/tools/Acquisition',
                '/napari/tools/Classification',
                '/napari/tools/Measurement',
                '/napari/tools/Segmentation',
                '/napari/tools/Transform',
                '/napari/tools/Utilities',
                '/napari/tools/Visualization',
                ]


# user provides this
class _MenuItem(BaseModel):
    when: Optional[str] = Field(
        description="Condition which must be true to show this item"
    )
    group: Optional[str] = Field(description="Group into which this item belongs")


class Submenu(_MenuItem):
    submenu: str = Field(
        ...,
        description="Identifier of the submenu to display in this item."
        "The submenu must be declared in the 'submenus' -section",
    )
    # if submenu doesn't exist, you get:
    # Menu item references a submenu ...` which is not defined in the 'submenus' section


class MenuCommand(_MenuItem, Executable):
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
    # if command doesn't exist, you get:
    # "Menu item references an alt-command  `...` which is not defined in
    # the 'commands' section."


MenuItem = Union[MenuCommand, Submenu]
