from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from .manifest import PluginManifest
from pathlib import Path

if TYPE_CHECKING:
    from .manifest.menus import MenuItem
    from .manifest.commands import CommandContribution
    from .manifest.submenu import SubmenuContribution
    from .manifest.themes import ThemeContribution
    from .manifest.io import ReaderContribution


PluginKey = str  # this is defined on PluginManifest as `publisher.name`


class PluginManager:
    _manifests: Dict[PluginKey, PluginManifest] = {}
    _commands: Dict[str, Tuple[CommandContribution, PluginKey]] = {}
    _submenus: Dict[str, SubmenuContribution] = {}
    _themes: Dict[str, ThemeContribution] = {}
    _readers: DefaultDict[str, List[ReaderContribution]] = DefaultDict(list)

    def __init__(self) -> None:
        self.discover()  # TODO: should we be immediately discovering?

    def discover(self):
        self._manifests.clear()
        self._commands.clear()
        self._submenus.clear()
        self._themes.clear()
        self._readers.clear()

        for mf in PluginManifest.discover():
            self._manifests[mf.key] = mf
            if mf.contributes:
                for cmd in mf.contributes.commands or []:
                    self._commands[cmd.command] = (cmd, mf.key)
                for subm in mf.contributes.submenus or []:
                    self._submenus[subm.id] = subm
                for theme in mf.contributes.themes or []:
                    self._themes[theme.id] = theme
                for reader in mf.contributes.readers or []:
                    for pattern in reader.filename_patterns:
                        self._readers[pattern].append(reader)
                    if reader.accepts_directories:
                        self._readers[""].append(reader)

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self._manifests.values():
            if mf.contributes:
                yield from getattr(mf.contributes.menus, menu_key, [])

    def get_command(self, command_id: str) -> CommandContribution:
        return self._commands[command_id][0]

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        return self._submenus[submenu_id]

    def activate(self, key: PluginKey):
        try:
            plugin = self._manifests[key]
        except KeyError:
            raise KeyError(f"Cannot activate unrecognized plugin key {key!r}")

        try:
            plugin.activate()
        except Exception as e:
            raise type(e)(f"Activating plugin {key!r} failed: {e}")

    def iter_compatible_readers(
        self, path: Union[str, Path]
    ) -> Iterator[ReaderContribution]:
        from fnmatch import fnmatch

        if Path(path).is_dir():
            yield from self._readers[""]
        else:
            seen: Set[str] = set()
            for ext, readers in self._readers.items():
                if ext and fnmatch(str(path), ext):
                    for r in readers:
                        if r.command in seen:
                            continue
                        seen.add(r.command)
                        yield r


plugin_manager = PluginManager()
