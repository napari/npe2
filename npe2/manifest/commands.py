from typing import Optional, Union

from pydantic import BaseModel, Field

from .icon import Icon


class CommandContribution(BaseModel):
    """Contribute a command.

    Contribute the UI for a command consisting of a title and (optionally) an
    icon, category, and enabled state. Enablement is expressed with when
    clauses. By default, commands show in the Command Palette (⇧⌘P) but they
    can also show in other menus.

    Presentation of contributed commands depends on the containing menu. The
    Command Palette, for instance, prefixes commands with their category,
    allowing for easy grouping. However, the Command Palette doesn't show icons
    nor disabled commands. The editor context menu, on the other hand, shows
    disabled items but doesn't show the category label.

    Note: When a command is invoked (from a key binding, from the Command
    Palette, any other menu, or programmatically), VS Code will emit an
    activationEvent onCommand:${command}.
    """

    command: str = Field(..., description="Identifier of the command to execute")
    title: str = Field(
        ..., description="Title by which the command is represented in the UI"
    )
    short_title: Optional[str] = Field(
        None,
        description="(Optional) Short title by which the command is "
        "represented in the UI",
    )
    category: Optional[str] = Field(
        None,
        description="(Optional) Category string by the command is grouped in the UI",
    )
    icon: Optional[Union[str, Icon]] = Field(
        None,
        description=(
            "(Optional) Icon which is used to represent the command in the UI."
            " Either a file path, an object with file paths for dark and light"
            "themes, or a theme icon references, like `$(zap)`"
        ),
    )
    enablement: Optional[str] = Field(
        None,
        description=(
            "(Optional) Condition which must be true to enable the command in the UI "
            "(menu and keybindings). Does not prevent executing the command "
            "by other means, like the `executeCommand` api."
        ),
    )
    python_name: Optional[str] = Field(
        None,
        description="(Optional) Fully qualified name to callable python object "
        "implementing this command. This usually takes the form of "
        "`{obj.__module__}.{obj.__qualname__} (e.g. `my_package.a_module.some_function`). "
        "If provided, using `register_command` in the plugin activate function is optional "
        "(but takes precedence).",
    )
