from typing import List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, root_validator

from .utils import Executable

# # napari provides these
# class Menu(BaseModel):
#     key: str
#     id: int
#     description: str
#     supports_submenus: bool = True
#     deprecation_message: Optional[str]


# napari_menus = [
#     Menu(key="command_pallete", id=0, description="The Command Palette"),
#     Menu(
#         key="layers__context", id=1, description="The layer list context menu"
#     ),
#     Menu(
#         key="layers__context", id=1, description="The layer list context menu"
#     ),
# ]


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


# how to do something like layers/context
class MenusContribution(BaseModel):
    # TODO: list of (str, menu item) coerce to dict/MenuItem
    # TODO: define convention around strings
    command_pallete: Optional[List[MenuItem]]
    layers__context: Optional[List[MenuItem]]
    plugins__widgets: Optional[List[MenuItem]]
    test_menu: Optional[List[MenuItem]]

    class Config:
        extra = "allow"

    @root_validator
    def _validate_extra(cls, values: dict):
        """Plugins may declare custom menu IDs... we make sure they are valid here.

        They become accessible as attributes on the MenusContribution instance.
        """

        # get validator... all of these fields have the same type
        # (Optional[List[MenuItem]])
        validate = list(MenusContribution.__fields__.values())[0].validate

        for i, (key, val) in enumerate(values.items()):
            if key not in cls.__fields__:
                val, err = validate(val, {}, loc=str(i))
                if err:  # pragma: no cover
                    raise ValidationError([err], cls)
                values[key] = val
        return values
