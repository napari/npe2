from typing import Generic, TypeVar

from typing_extensions import Protocol


class ProvidesCommand(Protocol):
    command: str


R = TypeVar("R")


class Executable(Generic[R]):
    def exec(self: ProvidesCommand, args: tuple = (), kwargs: dict = {}) -> R:
        from .._command_registry import execute_command

        return execute_command(self.command, args, kwargs)
