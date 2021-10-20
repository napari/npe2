from __future__ import annotations

__all__ = ["PluginContext", "PluginManager"]
import sys
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from ._command_registry import CommandRegistry
from .manifest import PluginManifest

if TYPE_CHECKING:
    from .manifest.commands import CommandContribution
    from .manifest.io import ReaderContribution
    from .manifest.menus import MenuItem
    from .manifest.submenu import SubmenuContribution
    from .manifest.themes import ThemeContribution


PluginKey = str  # this is defined on PluginManifest as `publisher.name`


class _ContributionsIndex:
    _submenus: Dict[str, SubmenuContribution] = {}
    _commands: Dict[str, Tuple[CommandContribution, PluginKey]] = {}
    _themes: Dict[str, ThemeContribution] = {}
    _readers: DefaultDict[str, List[ReaderContribution]] = DefaultDict(list)

    def get_command(self, command_id: str) -> CommandContribution:
        return self._commands[command_id][0]

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        return self._submenus[submenu_id]


class PluginManager:
    __instance: Optional[PluginManager] = None  # a global instance
    _contrib: _ContributionsIndex

    def __init__(self, reg: Optional[CommandRegistry] = None) -> None:
        self._command_registry = reg or CommandRegistry()
        self._contexts: Dict[PluginKey, PluginContext] = {}
        self._manifests: Dict[PluginKey, PluginManifest] = {}
        self.discover()  # TODO: should we be immediately discovering?

    @property
    def commands(self) -> CommandRegistry:
        return self._command_registry

    def discover(self, paths: Sequence[str] = ()) -> None:
        """Discover and index plugin manifests in the environment.

        Parameters
        ----------
        paths : Sequence[str], optional
            Optional list of strings to insert at front of sys.path when discovering.
        """
        self._contrib = _ContributionsIndex()
        self._manifests.clear()

        for result in PluginManifest.discover(paths=paths):
            if result.manifest is None:
                continue
            mf = result.manifest
            self._manifests[mf.key] = mf
            if mf.contributions:
                for cmd in mf.contributions.commands or []:
                    self._contrib._commands[cmd.id] = (cmd, mf.key)
                for subm in mf.contributions.submenus or []:
                    self._contrib._submenus[subm.id] = subm
                for theme in mf.contributions.themes or []:
                    self._contrib._themes[theme.id] = theme
                for reader in mf.contributions.readers or []:
                    for pattern in reader.filename_patterns:
                        self._contrib._readers[pattern].append(reader)
                    if reader.accepts_directories:
                        self._contrib._readers[""].append(reader)

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self._manifests.values():
            if mf.contributions:
                yield from getattr(mf.contributions.menus, menu_key, [])

    def activate(self, key: PluginKey) -> PluginContext:
        # TODO: this is an important function... should be carefully considered
        try:
            mf = self._manifests[key]
        except KeyError:
            raise KeyError(f"Cannot activate unrecognized plugin key {key!r}")

        # create the context that will be with this plugin for its lifetime.
        ctx = self.get_context(key)
        if ctx._activated:
            # prevent "reactivation"
            return ctx

        try:
            modules_pre = set(sys.modules)
            mf.activate(ctx)
            # store the modules imported by plugin activation
            # (not sure if useful yet... but could be?)
            ctx._imports = set(sys.modules).difference(modules_pre)
            ctx._activated = True
        except Exception as e:  # pragma: no cover
            self._contexts.pop(key, None)
            raise type(e)(f"Activating plugin {key!r} failed: {e}") from e

        if mf.contributions and mf.contributions.commands:
            for cmd in mf.contributions.commands:
                if cmd.python_name and cmd.id not in self.commands:
                    self.commands._register_python_name(cmd.id, cmd.python_name)

        return ctx

    def deactivate(self, key: PluginKey) -> None:
        if key not in self._contexts:
            return
        plugin = self._manifests[key]
        plugin.deactivate()
        ctx = self._contexts.pop(key)
        ctx._dispose()

    def iter_compatible_readers(
        self, path: Union[str, Path]
    ) -> Iterator[ReaderContribution]:
        from fnmatch import fnmatch

        if isinstance(path, list):
            return NotImplemented
        if Path(path).is_dir():
            yield from self._contrib._readers[""]
        else:
            seen: Set[str] = set()
            for ext, readers in self._contrib._readers.items():
                if ext and fnmatch(str(path), ext):
                    for r in readers:
                        if r.command in seen:
                            continue
                        seen.add(r.command)
                        yield r

    @classmethod
    def instance(cls) -> PluginManager:
        """Singleton instance."""
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def get_context(self, plugin_key: PluginKey) -> PluginContext:
        if plugin_key not in self._contexts:
            self._contexts[plugin_key] = PluginContext(plugin_key, reg=self.commands)
        return self._contexts[plugin_key]


class PluginContext:
    """An object that can contain information for a plugin over its lifetime."""

    # stores all created contexts (currently cleared by `PluginManager.deactivate`)

    def __init__(
        self, plugin_key: PluginKey, reg: Optional[CommandRegistry] = None
    ) -> None:
        self._activated = False
        self.plugin_key = plugin_key
        self._command_registry = reg or PluginManager.instance().commands
        self._imports: Set[str] = set()  # modules that were imported by this plugin
        self._disposables: Set[Callable] = set()  # functions to call when deactivating

    def register_command(self, id: str, command: Optional[Callable] = None):
        def _inner(command):
            self._disposables.add(self._command_registry.register(id, command))
            return command

        return _inner if command is None else _inner(command)

    def _dispose(self):
        for dispose in self._disposables:
            dispose()
