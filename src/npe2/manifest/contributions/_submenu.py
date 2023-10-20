from typing import Optional, Union

from npe2._pydantic_compat import BaseModel, Field

from ._icon import Icon


class SubmenuContribution(BaseModel):
    id: str = Field(description="Identifier of the menu to display as a submenu.")
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
