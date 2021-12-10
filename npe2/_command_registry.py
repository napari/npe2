# flake8: noqa
from __future__ import annotations

from functools import partial
from typing import Any, Callable, Dict, Optional, Union

PDisposable = Callable[[], None]
import re
from dataclasses import dataclass
from importlib import import_module

from psygnal import Signal

from .manifest.commands import _dotted_name

_dotted_name_pattrn = re.compile(_dotted_name)


@dataclass
class CommandHandler:
    id: str
    function: Optional[Callable] = None
    python_name: Optional[str] = None

    def resolve(self) -> Callable:
        if self.function is not None:
            return self.function
        if self.python_name is None:
            raise RuntimeError("cannot resolve command without python_name")

        try:
            module_name, class_name = self.python_name.rsplit(":", 1)
            module = import_module(module_name)
            self.function = getattr(module, class_name)
        except Exception as e:
            raise RuntimeError("Failed to import command at {self.python_name!r}: {e}")
        return self.function


class CommandRegistry:
    commandRegistered = Signal(str)
    commandUnregistered = Signal(str)

    def __init__(self) -> None:
        self._commands: Dict[str, CommandHandler] = {}

    # similar to:
    # https://github.com/microsoft/vscode/blob/main/src/vs/platform/commands/common/commands.ts#L61
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
            if not _dotted_name_pattrn.match(command):
                raise ValueError(
                    "String command {command!r} is not a valid qualified python path."
                )
            cmd = CommandHandler(id, python_name=command)
        elif not callable(command):
            raise TypeError(f"Cannot register non-callable command: {command}")
        else:
            cmd = CommandHandler(id, function=command)

        # TODO: validate arguments and type constraints
        # possibly wrap command in a type validator?

        self._commands[id] = cmd
        self.commandRegistered.emit(id)

        return partial(self.unregister, id)

    def unregister(self, id: str):
        if id in self._commands:
            del self._commands[id]
            self.commandUnregistered.emit(id)

    def get(self, id: str) -> Callable:
        # FIXME: who should control activation?
        if id not in self._commands:
            from ._plugin_manager import PluginManager

            pm = PluginManager.instance()

            if id in pm._contrib._commands:
                _, plugin_key = pm._contrib._commands[id]
                pm.activate(plugin_key)
            if id not in self._commands:
                raise KeyError(f"command {id!r} not registered")
        return self._commands[id].resolve()

    def execute(self, id: str, args=(), kwargs={}) -> Any:
        return self.get(id)(*args, **kwargs)

    def __contains__(self, id: str):
        return id in self._commands
