# flake8: noqa
from __future__ import annotations
from functools import partial

from typing import Callable, Dict, List, NewType, Any, Optional, Type

PDisposable = Callable[[], None]

from psygnal import Signal


class CommandRegistry:
    _commands: Dict[str, Callable] = {}
    commandRegistered = Signal(str)

    # similar to:
    # https://github.com/microsoft/vscode/blob/main/src/vs/platform/commands/common/commands.ts#L61
    def register_command(self, id: str, command: Callable) -> PDisposable:
        if not isinstance(id, str) and id.strip():
            raise ValueError(
                f"Invalid command id for {command}, must be non-empty string"
            )
        if id in self._commands:
            raise ValueError(f"Command {id} already exists")
        if not callable(command):
            raise TypeError(f"Cannot register non-callable command: {command}")

        # TODO: validate argumemnts and type constraints
        # possibly wrap command in a type validator?

        self._commands[id] = command
        self.commandRegistered.emit(id)

        return partial(self.unregister_command, id)

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

        module_name, class_name = python_name.rsplit(".", 1)
        module = import_module(module_name)
        function = getattr(module, class_name)
        return self.register_command(id, function)

    def unregister_command(self, id: str):
        self._commands.pop(id, None)

    def get_command(self, id) -> Callable:
        # FIXME: who should control activation?
        if id not in self._commands:
            from ._plugin_manager import plugin_manager

            if id in plugin_manager._commands:
                _, plugin_key = plugin_manager._commands[id]
                plugin_manager.activate(plugin_key)
        if id not in self._commands:
            raise KeyError(f"command {id!r} not registered")
        return self._commands[id]

    def execute_command(self, id: str, args=(), kwargs={}):
        return self.get_command(id)(*args, **kwargs)

    def register_command_alias(self, existing_id: str, new_id: str):
        ...

    def __contains__(self, id: str):
        return id in self._commands


command_registry = CommandRegistry()
unregister_command = command_registry.unregister_command
get_command = command_registry.get_command
execute_command = command_registry.execute_command
# register_command_alias = command_registry.register_command_alias


def register_command(cmd_id: str, command: Optional[Callable] = None):
    if command is None:

        def register_decorator(cmd):
            command_registry.register_command(cmd_id, cmd)
            return cmd

        return register_decorator
    command_registry.register_command(cmd_id, command)
