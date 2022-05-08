from typing import List, Optional, Union

from pydantic import BaseModel, validator
from pydantic.fields import Field

from .. import _validators
from ._icon import Icon
from ._menus import MenuItem


class SubmenuContribution(BaseModel):
    id: str = Field(description="Identifier of the menu to display as a submenu.")
    _valid_id = validator("id", allow_reuse=True)(_validators.command_id)
    label: str = Field(
        description="The label of the menu item which leads to this submenu."
    )
    icon: Optional[Union[str, Icon]] = Field(
        None,
        description=(
            "(Optional) Icon which is used to represent the command in the UI."
            " Either a file path, an object with file paths for dark and light"
            "themes, or a theme icon references, like `$(zap)`"
        ),
    )
    contents: List[MenuItem] = Field(
        description="The contents of the submenu, commands and other submenus."
    )
