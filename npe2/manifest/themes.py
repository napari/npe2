from typing import Optional, Union

from pydantic import BaseModel
from pydantic.color import Color
from pydantic.fields import Field
from typing_extensions import Literal


class ThemeColors(BaseModel):
    canvas: Optional[Color]
    console: Optional[Color]
    background: Optional[Color]
    foreground: Optional[Color]
    primary: Optional[Color]
    secondary: Optional[Color]
    highlight: Optional[Color]
    text: Optional[Color]
    icon: Optional[Color]
    warning: Optional[Color]
    current: Optional[Color]


class ThemeContribution(BaseModel):
    label: str = Field(description="Label of the color theme as shown in the UI.")
    id: str = Field(description="Id of the color theme as used in the user settings.")
    type: Union[Literal["dark"], Literal["light"]] = Field(
        description="Base theme type, used for icons and filling in unprovided colors"
    )
    colors: ThemeColors = Field(description="Theme colors")
