from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Extra, Field, validator

from ..types import PythonName
from . import _validators

if TYPE_CHECKING:
    from .._command_registry import CommandRegistry


class CommandContribution(BaseModel):
    """Contribute a **command** (a python callable) consisting of a unique `id`,
    a `title` and (optionally) a `python_path` that points to a fully qualified python
    callable.  If a `python_path` is not included in the manifest, it *must* be
    registered during activation with `register_command`.

    Note, some other contributions (e.g. `readers`, `writers` and `widgets`) will
    *point* to a specific command.  The command itself (i.e. the callable python
    object) will always appear in the `contributions.commands` section, but those
    contribution types may add additional contribution-specific metadata.

    ```{admonition} Future Plans
    Command contributions will eventually include an **icon**, **category**, and
    **enabled** state. Enablement is expressed with *when clauses*, that capture a
    conditional expression determining whether the command should be enabled or not,
    based on the current state of the program.  (i.e. "*If the active layer is a
    `Labels` layer*")

    Commands will eventually be availble in a Command Palette (accessible with a
    hotkey) but they can also show in other menus.
    ```
    """

    id: str = Field(
        ...,
        description=dedent(
            "A unique identifier used to reference this command. While this may look "
            "like a python fully qualified name this does *not* refer to a python "
            "object; this identifier is specific to napari.  It must begin with "
            "the name of the package, and include only alphanumeric characters, plus "
            "dashes and underscores."
        ),
    )
    _valid_id = validator("id", allow_reuse=True)(_validators.command_id)

    title: str = Field(
        ...,
        description="User facing title representing the command. This might be used, "
        "for example, when searching in a command palette. Examples: 'Generate lily "
        "sample', 'Read tiff image', 'Open gaussian blur widget'. ",
    )
    python_name: Optional[PythonName] = Field(
        None,
        description="Fully qualified name to a callable python object "
        "implementing this command. This usually takes the form of "
        "`{obj.__module__}:{obj.__qualname__}` "
        "(e.g. `my_package.a_module:some_function`)",
    )
    _valid_pyname = validator("python_name", allow_reuse=True)(_validators.python_name)

    # short_title: Optional[str] = Field(
    #     None,
    #     description="Short title by which the command is "
    #     "represented in the UI",
    # )
    # category: Optional[str] = Field(
    #     None,
    #     description="Category string by the command is grouped in the UI",
    # )
    # icon: Optional[Union[str, Icon]] = Field(
    #     None,
    #     description=(
    #         "Icon which is used to represent the command in the UI."
    #         " Either a file path, an object with file paths for dark and light"
    #         "themes, or a theme icon references, like `$(zap)`"
    #     ),
    # )
    # enablement: Optional[str] = Field(
    #     None,
    #     description=(
    #         "Condition which must be true to enable the command in the UI "
    #         "(menu and keybindings). Does not prevent executing the command "
    #         "by other means, like the `executeCommand` api."
    #     ),
    # )

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
