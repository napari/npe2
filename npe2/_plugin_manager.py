from __future__ import annotations

from npe2.manifest.io import WriterContribution

__all__ = ["plugin_manager", "PluginContext", "PluginManager"]  # noqa: F822
import sys
from pathlib import Path
from typing import TYPE_CHECKING, DefaultDict, Dict, Iterator, List, Set, Tuple, Union

from .manifest import PluginManifest

if TYPE_CHECKING:
    from .manifest.commands import CommandContribution
    from .manifest.io import ReaderContribution
    from .manifest.menus import MenuItem
    from .manifest.submenu import SubmenuContribution
    from .manifest.themes import ThemeContribution


PluginKey = str  # this is defined on PluginManifest as `publisher.name`


class PluginContext:
    """An object that can contain information for a plugin over its lifetime."""

    # stores all created contexts (currently cleared by `PluginManager.deactivate`)
    _contexts: Dict[PluginKey, PluginContext] = {}

    def __init__(self, plugin_key: PluginKey) -> None:
        self._plugin_key = plugin_key
        self._imports: Set[str] = set()  # modules that were imported by this plugin
        PluginContext._contexts[plugin_key] = self

    @classmethod
    def get_or_create(cls, plugin_key: PluginKey) -> PluginContext:
        if plugin_key not in cls._contexts:
            PluginContext(plugin_key)
        return cls._contexts[plugin_key]


class PluginManager:
    _manifests: Dict[PluginKey, PluginManifest] = {}
    _commands: Dict[str, Tuple[CommandContribution, PluginKey]] = {}
    _submenus: Dict[str, SubmenuContribution] = {}
    _themes: Dict[str, ThemeContribution] = {}
    _readers: DefaultDict[str, List[ReaderContribution]] = DefaultDict(list)

    _writers_by_extension: DefaultDict[str, List[str]] = DefaultDict(list)
    _writers_by_type: DefaultDict[str, List[str]] = DefaultDict(list)

    def __init__(self) -> None:
        self.discover()  # TODO: should we be immediately discovering?

    def discover(self):
        self._manifests.clear()
        self._commands.clear()
        self._submenus.clear()
        self._themes.clear()
        self._readers.clear()
        self._writers_by_extension.clear()
        self._writers_by_type.clear()

        for mf in PluginManifest.discover():
            self._manifests[mf.key] = mf
            if mf.contributions:
                for cmd in mf.contributions.commands or []:
                    self._commands[cmd.id] = (cmd, mf.key)
                for subm in mf.contributions.submenus or []:
                    self._submenus[subm.id] = subm
                for theme in mf.contributions.themes or []:
                    self._themes[theme.id] = theme
                for reader in mf.contributions.readers or []:
                    for pattern in reader.filename_patterns:
                        self._readers[pattern].append(reader)
                    if reader.accepts_directories:
                        self._readers[""].append(reader)
                for writer in mf.contributions.writers or []:
                    # Index the writer by compatible file extension.
                    # Note: this relys on normalization rules applied during
                    #       validation. Want forms like: .ext
                    for ext in writer.filename_extensions:
                        self._writers_by_extension[ext].append(writer.command)
                    # Index the writer by compatible layer type.
                    # Note: this depends on a LayerType.all values being coerced
                    #       during WriterContribution construction. The `all`
                    #       layer_type shouldn't appear here.
                    for kind in writer.layer_types:
                        self._writers_by_type[kind].append(writer.command)

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self._manifests.values():
            if mf.contributions:
                yield from getattr(mf.contributions.menus, menu_key, [])

    def get_command(self, command_id: str) -> CommandContribution:
        return self._commands[command_id][0]

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        return self._submenus[submenu_id]

    def activate(self, key: PluginKey) -> PluginContext:
        # TODO: this is an important function... should be carefully considered
        try:
            pm = self._manifests[key]
        except KeyError:
            raise KeyError(f"Cannot activate unrecognized plugin key {key!r}")

        # TODO: prevent "reactivation"

        # create the context that will be with this plugin for its lifetime.
        ctx = PluginContext.get_or_create(key)
        try:
            modules_pre = set(sys.modules)
            pm.activate(ctx)
            # store the modules imported by plugin activation
            # (not sure if useful yet... but could be?)
            ctx._imports = set(sys.modules).difference(modules_pre)
        except Exception as e:
            PluginContext._contexts.pop(key, None)
            raise type(e)(f"Activating plugin {key!r} failed: {e}")

        if pm.contributions and pm.contributions.commands:
            for cmd in pm.contributions.commands:
                from ._command_registry import command_registry

                if cmd.python_name and cmd.id not in command_registry:
                    command_registry._register_python_name(cmd.id, cmd.python_name)

        return ctx

    def deactivate(self, key: PluginKey) -> None:
        if key not in PluginContext._contexts:
            return
        plugin = self._manifests[key]
        plugin.deactivate()
        del PluginContext._contexts[key]  # TODO: probably want to do more here

    def iter_compatible_readers(
        self, path: Union[str, Path]
    ) -> Iterator[ReaderContribution]:
        from fnmatch import fnmatch

        if isinstance(path, list):
            return NotImplemented
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

    def iter_compatible_writers(
        self, layer_types: List[str], file_extension: str
    ) -> Iterator[WriterContribution]:
        candidates = set(self._writers_by_extension[file_extension])
        for kind in layer_types:
            candidates &= set(self._writers_by_type[kind])
        yield from (
            WriterContribution(
                command=cmd, layer_types=layer_types, file_extensions=[file_extension]
            )
            for cmd in candidates
        )


_GLOBAL_PM = None


def __getattr__(name):
    if name == "plugin_manager":
        global _GLOBAL_PM
        if _GLOBAL_PM is None:
            try:
                _GLOBAL_PM = PluginManager()
            except Exception as e:
                print(f"Failed to initialize plugin manager: {e}")
                raise
        return _GLOBAL_PM
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
