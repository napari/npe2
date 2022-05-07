from typing import List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, root_validator

from ..utils import Executable

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


# define the valid locations that menu items can populate
class MenusContribution(BaseModel):
    napari__plugins: Optional[List[MenuItem]]
    napari__layer_context: Optional[List[MenuItem]]

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def _coerce_locations(cls, values):
        """Map plugin menu locations provided in the plugin manifest.

        Plugins are able to contribute menu items to certain locations in napari.
        In the plugin manifest these locations must begin with a '/'. The valid
        locations are '/napari/plugins' and '/napari/layer_context'.
        """
        # map from manifest provided menu locations to MenusContribution keys
        # this mapping removes the initial '/' and replaces subsequent `'/'
        # with '__'.
        menu_contributions = {}
        for key, val in values.items():
            # menu locations must begin with a `/`
            if key[0] == "/":
                menu_name = key[1:].replace("/", "__")
                if menu_name not in list(MenusContribution.__fields__.keys()):
                    raise ValueError(
                        "Manifest provided menu location does not match"
                        " valid menu contribution location"
                    )
                menu_contributions[menu_name] = val
            else:
                menu_contributions[key] = val
        return menu_contributions

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
