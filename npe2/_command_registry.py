# flake8: noqa
from __future__ import annotations
from functools import partial

from typing import Callable, Dict, List, NewType, Any, Optional

PDisposable = Callable[[], None]

from psygnal import Signal


class CommandRegistry:
    _commands: Dict[str, Callable] = {}
    commandRegistered = Signal(str)

    # similar to:
    # https://github.com/microsoft/vscode/blob/main/src/vs/platform/commands/common/commands.ts#L61
    def register_command(self, id: str, command: Callable) -> PDisposable:
        if not isinstance(id, str) and id.strip():
            raise ValueError("invalid id, must be string with content")
        if id in self._commands:
            raise ValueError(f"command {id} already exists")

        # TODO: validate argumemnts and type constraints
        # possibly wrap command in a type validator?

        self._commands[id] = command
        self.commandRegistered.emit(id)

        return partial(self.unregister_command, id)

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
