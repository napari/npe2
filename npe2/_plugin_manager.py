from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, List, Tuple
from .manifest import PluginManifest

if TYPE_CHECKING:
    from .manifest.menus import MenuItem
    from .manifest.commands import CommandContribution
    from .manifest.submenu import SubmenuContribution


PluginKey = str


class PluginManager:
    _manifests: Dict[PluginKey, PluginManifest] = {}
    _commands: Dict[str, Tuple[CommandContribution, PluginKey]] = {}
    _submenus: Dict[str, SubmenuContribution] = {}

    def __init__(self) -> None:
        self.discover()  # TODO: should we be immediately discovering?

    def discover(self):
        self._manifests.clear()
        self._commands.clear()
        self._submenus.clear()

        for mf in PluginManifest.discover():
            self._manifests[mf.key] = mf
            if mf.contributes:
                for cmd in mf.contributes.commands or []:
                    self._commands[cmd.command] = (cmd, mf.key)
                for subm in mf.contributes.submenus or []:
                    self._submenus[subm.id] = subm

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self._manifests.values():
            if mf.contributes:
                yield from getattr(mf.contributes.menus, menu_key, [])

    def get_command(self, command_id: str) -> CommandContribution:
        return self._commands[command_id][0]

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        return self._submenus[submenu_id]

    def activate(self, key: PluginKey):
        self._manifests[key].activate()


plugin_manager = PluginManager()
