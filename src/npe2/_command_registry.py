from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Union

from psygnal import Signal

from .manifest import utils
from .manifest._validators import DOTTED_NAME_PATTERN
from .types import PythonName

PDisposable = Callable[[], None]

if TYPE_CHECKING:
    from .manifest.schema import PluginManifest


@dataclass
class CommandHandler:
    id: str
    function: Optional[Callable] = None
    python_name: Optional[PythonName] = None

    def resolve(self) -> Callable:
        if self.function is not None:
            return self.function
        if self.python_name is None:
            raise RuntimeError("cannot resolve command without python_name")

        try:
            self.function = utils.import_python_name(self.python_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to import command at {self.python_name!r}: {e}"
            ) from e

        return self.function


class CommandRegistry:
    """Registry of commands, updated on `PluginManager.activate`.

    `PluginManager.activate` is only run on `CommandRegistry.get` (when we resolve the
    callable object for a command). This means that commands from enabled plugins are
    not added to `CommandRegistry` until a command from that plugin is executed.
    """

    command_registered = Signal(str)
    command_unregistered = Signal(str)

    def __init__(self) -> None:
        self._commands: Dict[str, CommandHandler] = {}

    def register(self, id: str, command: Union[Callable, str]) -> PDisposable:
        """Register a command under `id`.

        Parameters
        ----------
        id : str
            A unique key with which to refer to this command
        command : Union[Callable, str]
            Either a callable object, or (if a string) the fully qualified name of a
            python object.  If a string is provided, it is not imported until
            the command is actually executed.

        Returns
        -------
        PDisposable
            A callable that, when called, unregisters the command.

        Raises
        ------
        ValueError
            If the id is not a non-empty string, or if it already exists.
        TypeError
            If `command` is not a string or a callable object.
        """
        if not (isinstance(id, str) and id.strip()):
            raise ValueError(
                f"Invalid command id for {command}, must be non-empty string"
            )
        if id in self._commands:
            raise ValueError(f"Command {id} already exists")

        if isinstance(command, str):
            if not DOTTED_NAME_PATTERN.match(command):
                raise ValueError(
                    "String command {command!r} is not a valid qualified python path."
                )
            cmd = CommandHandler(id, python_name=PythonName(command))
        elif not callable(command):
            raise TypeError(f"Cannot register non-callable command: {command}")
        else:
            cmd = CommandHandler(id, function=command)

        # TODO: validate arguments and type constraints
        # possibly wrap command in a type validator?

        self._commands[id] = cmd
        self.command_registered.emit(id)

        return partial(self.unregister, id)

    def unregister(self, id: str):
        """Unregister command with key `id`.  No-op if key doesn't exist."""
        if id in self._commands:
            del self._commands[id]
            self.command_unregistered.emit(id)

    def register_manifest(self, mf: PluginManifest) -> None:
        """Register all commands in a manifest"""
        if mf.contributions and mf.contributions.commands:
            for cmd in mf.contributions.commands:
                if cmd.python_name and cmd.id not in self:
                    self.register(cmd.id, cmd.python_name)

    def unregister_manifest(self, mf: PluginManifest) -> None:
        """Unregister all commands in a manifest"""
        if mf.contributions and mf.contributions.commands:
            for cmd in mf.contributions.commands:
                if cmd.id in self:
                    self.unregister(cmd.id)

    def get(self, id: str) -> Callable:
        """Get callable object for command `id`."""
        # FIXME: who should control activation?
        if id not in self._commands:
            from ._plugin_manager import PluginManager

            pm = PluginManager.instance()

            if id in pm._contrib._commands:
                _, plugin_key = pm._contrib._commands[id]
                pm.activate(plugin_key)
            if id not in self._commands:  # sourcery skip
                raise KeyError(f"command {id!r} not registered")
        return self._commands[id].resolve()

    def execute(self, id: str, args=(), kwargs=None) -> Any:
        if kwargs is None:
            kwargs = {}
        return self.get(id)(*args, **kwargs)

    def __contains__(self, id: str):
        return id in self._commands
