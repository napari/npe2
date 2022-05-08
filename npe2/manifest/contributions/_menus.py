from collections import namedtuple
from typing import Optional, Union

from pydantic import BaseModel, Field

from ..utils import Executable


Menu = namedtuple('Menu', 'key description')

# a list of valid napari menu locations that plugins can contribute too.
# keys provided in the plugin manifest must match these strings
napari_menus = [Menu('/napari/layer_context', "Process Layer"),
                Menu('/napari/layer_context/projections', "Make Projection"),
                Menu('/napari/layer_context/convert_type', "Convert datatype"),
                Menu('/napari/tools/acquisition', "Acquisition"),
                Menu('/napari/tools/classification', "Classification"),
                Menu('/napari/tools/measurement', "Measurement"),
                Menu('/napari/tools/segmentation', "Segmentation"),
                Menu('/napari/tools/transform', "Transform"),
                Menu('/napari/tools/utilities', "Utilities"),
                Menu('/napari/tools/visualization', "Visualization"),
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
