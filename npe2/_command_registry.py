# flake8: noqa
from __future__ import annotations
from functools import partial

from typing import Callable, Dict, List, NewType, Any, Optional

Command = Callable
CommandID = str
PDisposable = Callable[[], None]


class CommandRegistry:
    _commands: Dict[CommandID, Command] = {}

    # similar to extHostCommands.ts-ExtHostCommands.registerCommand
    def register_command(self, id: CommandID, command: Command) -> PDisposable:
        if not id.strip():
            raise ValueError("invalid id")
        if id in self._commands:
            raise ValueError(f"command {id} already exists")

        self._commands[id] = command
        # TODO: emit "did-register" signal
        return partial(self.unregister_command, id)

    def unregister_command(self, id: CommandID):
        self._commands.pop(id, None)

    def execute_command(self, id: CommandID, args=(), kwargs={}):
        if id not in self._commands:
            from ._plugin_manager import plugin_manager

            if id in plugin_manager._commands:
                _, plugin_key = plugin_manager._commands[id]
                plugin_manager.activate(plugin_key)

        try:
            return self._commands[id](*args, **kwargs)
        except KeyError:
            raise KeyError(f"command {id!r} not registered")

    def register_command_alias(self, existing_id: str, new_id: str):
        ...


command_registry = CommandRegistry()
unregister_command = command_registry.unregister_command
execute_command = command_registry.execute_command
# register_command_alias = command_registry.register_command_alias


def register_command(cmd_id: str, command: Optional[Command] = None):
    if command is None:

        def register_decorator(cmd):
            command_registry.register_command(cmd_id, cmd)
            return cmd

        return register_decorator
    command_registry.register_command(cmd_id, command)
