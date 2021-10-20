from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from typing_extensions import Protocol

if TYPE_CHECKING:
    from .._command_registry import CommandRegistry

R = TypeVar("R")


class ProvidesCommand(Protocol):
    command: str


class Executable(Generic[R]):
    def exec(
        self: ProvidesCommand,
        args: tuple = (),
        kwargs: dict = {},
        _registry: Optional[CommandRegistry] = None,
    ) -> R:
        if _registry is None:

            from .._plugin_manager import PluginManager

            _registery = PluginManager.instance().commands

        return _registery.execute(self.command, args, kwargs)
