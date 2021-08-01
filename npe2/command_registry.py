# flake8: noqa
from __future__ import annotations

from typing import Callable, Dict, List, NewType, Optional, Protocol, Any

Emitter = Any
CommandHandler = Callable
CommandID = NewType("CommandID", str)


class PDisposable(Protocol):
    def dispose(self):
        ...


class PCommandHandlerDescription(Protocol):
    description: str
    args: List[object]
    returns: Optional[str]


class PCommand(Protocol):
    id: CommandID
    handler: CommandHandler
    description: Optional[str]


class PCommandRegistry(Protocol):
    onDidRegisterCommand: Emitter

    def registerCommand(self, id: CommandID, command: CommandHandler) -> PDisposable:
        ...

    def registerCommandAlias(self, oldId: CommandID, newId: CommandID) -> PDisposable:
        ...

    def getCommand(self, id: CommandID) -> Optional[PCommand]:
        ...

    def getCommands(self) -> Dict[str, PCommand]:
        ...


class CommandRegistry(PCommandRegistry):
    _commands: Dict[CommandID, CommandHandler]

    def registerCommand(self, id: CommandID, command: CommandHandler) -> PDisposable:
        if not id.strip():
            raise ValueError("invalid id")
        if id in self._commands:
            raise ValueError(f"command {id} already exists")

        self._commands[id] = command

        return lambda: self.unregisterCommand(id)
