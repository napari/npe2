from typing import TYPE_CHECKING, Any, Optional, Union

from npe2._pydantic_compat import BaseModel, Extra, Field, validator
from npe2.manifest import _validators
from npe2.types import PythonName

from ._icon import Icon

if TYPE_CHECKING:
    from npe2._command_registry import CommandRegistry


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
        description="A unique identifier used to reference this command. While this may"
        " look like a python fully qualified name this does *not* refer to a python "
        "object; this identifier is specific to napari.  It must begin with "
        "the name of the package, and include only alphanumeric characters, plus "
        "dashes and underscores.",
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

    short_title: Optional[str] = Field(
        None,
        description="Short title by which the command is represented in "
        "the UI. Menus pick either `title` or `short_title` depending on the context "
        "in which they show commands.",
    )
    category: Optional[str] = Field(
        None,
        description="Category string by which the command may be grouped in the UI.",
    )
    icon: Optional[Union[str, Icon]] = Field(
        None,
        description="Icon used to represent this command in the UI, on "
        "buttons or in menus. These may be [superqt](https://github.com/napari/superqt)"
        " fonticon keys, such as `'fa6s.arrow_down'`; though note that plugins are "
        "expected to depend on any fonticon libraries they use, e.g "
        "[fonticon-fontawesome6](https://github.com/tlambert03/fonticon-fontawesome6).",
    )
    enablement: Optional[str] = Field(
        None,
        description=(
            "Expression which must evaluate as true to enable the command in the UI "
            "(menu and keybindings). Does not prevent executing the command "
            "by other means, like the `execute_command` api."
        ),
    )

    class Config:
        extra = Extra.forbid

    def exec(
        self,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        _registry: Optional["CommandRegistry"] = None,
    ) -> Any:
        if kwargs is None:
            kwargs = {}
        if _registry is None:
            from npe2._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.execute(self.id, args, kwargs)
