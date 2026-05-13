import sys
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_extra_types import color


# pydantic doesn't implement color equality?
class Color(color.Color):
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, color.Color):
            return False  # pragma: no cover
        return self.as_rgb_tuple() == __o.as_rgb_tuple()


class ThemeColors(BaseModel):
    """Optional color overrides for a contributed napari theme."""

    canvas: Color | None = None
    console: Color | None = None
    background: Color | None = None
    foreground: Color | None = None
    primary: Color | None = None
    secondary: Color | None = None
    highlight: Color | None = None
    text: Color | None = None
    icon: Color | None = None
    warning: Color | None = None
    error: Color | None = None
    current: Color | None = None


_color_keys = ", ".join([f"`{k}`" for k in ThemeColors.model_fields])
_color_args = "\n".join(
    [
        '- named colors: `"black"`, `"azure"`',
        '- hexadecimal values: `"0x000"`, `"#FFFFFF"`, `"7fffd4"`',
        "- RGB/RGBA tuples: `(255, 255, 255)`, `(255, 255, 255, 0.5)`",
        '- RGB/RGBA strings: `"rgb(255, 255, 255)"`, `"rgba(255, 255, 255, 0.5)"`',
        '- HSL strings: `"hsl(270, 60%, 70%)"`, `"hsl(270, 60%, 70%, .5)"`',
    ]
)


class ThemeContribution(BaseModel):
    """Contribute a color theme to napari.

    You must specify an **id**, **label**, and whether the theme is a dark theme or a
    light theme **type** so napari can derive matching icons and fallback colors.
    Any color keys omitted from the theme contribution will use the default napari
    dark/light theme colors for the selected base theme.
    """

    # TODO: do we need both id and label?
    id: str = Field(
        description="Identifier of the color theme as used in the user settings."
    )
    label: str = Field(description="Label of the color theme as shown in the UI.")
    type: Literal["dark", "light"] = Field(
        description="Base theme type, used for icons and filling in unprovided colors. "
        "Must be either `'dark'` or  `'light'`."
    )
    syntax_style: str | None = Field(
        default=None,
        description="Optional Pygments syntax style for napari's built-in console. "
        "If omitted, the base theme's style is used.",
    )
    colors: ThemeColors = Field(
        description=(
            f"Theme colors. Valid keys include: {_color_keys}. All keys are optional "
            "and omitted keys inherit from the selected base theme.\n\n"
            f"Color values can be defined via:\n{_color_args}"
        )
    )
    font_size: str = Field(
        default="12pt" if sys.platform == "darwin" else "9pt",
        description="Font size (in points, pt) used in the application.",
    )
