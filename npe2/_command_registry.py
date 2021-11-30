# flake8: noqa
from __future__ import annotations

from functools import partial
from typing import Any, Callable, Dict

PDisposable = Callable[[], None]

from psygnal import Signal


class CommandRegistry:
    commandRegistered = Signal(str)

    def __init__(self) -> None:
        self._commands: Dict[str, Callable] = {}

    # similar to:
    # https://github.com/microsoft/vscode/blob/main/src/vs/platform/commands/common/commands.ts#L61
    def register(self, id: str, command: Callable) -> PDisposable:
        if not isinstance(id, str) and id.strip():
            raise ValueError(
                f"Invalid command id for {command}, must be non-empty string"
            )
        if id in self._commands:
            raise ValueError(f"Command {id} already exists")
        if not callable(command):
            raise TypeError(f"Cannot register non-callable command: {command}")

        # TODO: validate arguments and type constraints
        # possibly wrap command in a type validator?

        self._commands[id] = command
        self.commandRegistered.emit(id)

        return partial(self.unregister, id)

    def _register_python_name(self, id: str, python_name: str) -> PDisposable:
        """Register a fully qualified `python_name` as command `id`

        Parameters
        ----------
        id : str
            Command id to register
        python_name : str
            Fully qualified name to python object (e.g. `my_package.submodule.function`)
        """
        from importlib import import_module

        module_name, class_name = python_name.rsplit(":", 1)
        module = import_module(module_name)
        function = getattr(module, class_name)
        return self.register(id, function)

    def unregister(self, id: str):
        self._commands.pop(id, None)

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
        return self._commands[id]

    def execute(self, id: str, args=(), kwargs={}) -> Any:
        return self.get(id)(*args, **kwargs)

    def __contains__(self, id: str):
        return id in self._commands
