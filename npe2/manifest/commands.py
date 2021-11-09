from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional, Union

from pydantic import BaseModel, Extra, Field

from .icon import Icon

if TYPE_CHECKING:
    from .._command_registry import CommandRegistry

_identifier = "([a-zA-Z_][a-zA-Z_0-9]+)"

# how do we deal with keywords ?
# do we try to validate ? Or do we just
# assume users won't try to create a command named
# `npe2_tester.False.if.for.in` ?
_dotted_name = f"(({_identifier}\\.)*{_identifier})"


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

    id: str = Field(
        ...,
        description=dedent(
            """
        Identifier of the command to execute

        While this may looks a python fully qualified name this does not refer
        to a python object.
        This identifier is specific to Napari, and will be considered unique.
        It follow the same rule as Python fully qualified name, with the extra
        restriction as being limited to ascii"""
        ),
        regex="^" + _dotted_name + "$",
    )
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
        "`{obj.__module__}:{obj.__qualname__} (e.g. "
        "`my_package.a_module:some_function`). If provided, using `register_command` "
        "in the plugin activate function is optional (but takes precedence).",
        regex=f"^{_dotted_name}:{_dotted_name}$",
    )

    class Config:
        extra = Extra.forbid

    def exec(
        self,
        args: tuple = (),
        kwargs: dict = {},
        _registry: Optional["CommandRegistry"] = None,
    ) -> Any:
        if _registry is None:
            from .._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.execute(self.id, args, kwargs)
