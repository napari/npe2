from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

from typing_extensions import Protocol

if TYPE_CHECKING:
    from .._command_registry import CommandRegistry

R = TypeVar("R")


class ProvidesCommand(Protocol):
    command: str


# TODO: add ParamSpec when it's supported better by mypy
class Executable(ProvidesCommand, Generic[R]):
    def exec(
        self,
        args: tuple = (),
        kwargs: dict = {},
        _registry: Optional[CommandRegistry] = None,
    ) -> R:
        return self.get_callable(_registry)(*args, **kwargs)

    def get_callable(
        self,
        _registry: Optional[CommandRegistry] = None,
    ) -> Callable[..., R]:
        if _registry is None:
            from .._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.get(self.command)

    @property
    def plugin_name(self: ProvidesCommand):
        # takes advantage of the fact that command always starts with manifest.name
        return self.command.split(".")[0]
