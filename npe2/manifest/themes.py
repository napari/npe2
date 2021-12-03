from typing import Optional, Union

from pydantic import BaseModel, color
from pydantic.fields import Field
from typing_extensions import Literal


# pydantic doesn't implement color equality?
class Color(color.Color):
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, color.Color):
            return False
        return self.as_rgb_tuple() == __o.as_rgb_tuple()


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
