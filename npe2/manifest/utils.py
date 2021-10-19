from typing import Any

from typing_extensions import Protocol


class ProvidesCommand(Protocol):
    command: str


class Executable:
    def exec(self: ProvidesCommand, args: tuple = (), kwargs: dict = {}) -> Any:
        from .._command_registry import execute_command

        return execute_command(self.command, args, kwargs)
