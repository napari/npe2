from __future__ import annotations

from npe2.manifest.io import LayerType, WriterContribution

__all__ = ["plugin_manager", "PluginContext", "PluginManager"]  # noqa: F822
import sys
from collections import Counter
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from warnings import warn

from intervaltree import IntervalTree

from ._command_registry import execute_command
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
    _writers_by_type: DefaultDict[
        LayerType, IntervalTree[WriterContribution]
    ] = DefaultDict(IntervalTree)

    def __init__(self) -> None:
        self.discover()  # TODO: should we be immediately discovering?

    def discover(self):
        """Finds and indexes npe2-based napari plugins installed in the python
        environment."""
        self._manifests.clear()
        self._commands.clear()
        self._submenus.clear()
        self._themes.clear()
        self._readers.clear()
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
                    for constraint in writer.layer_type_constraints():
                        self._writers_by_type.setdefault(
                            constraint.layer_type, IntervalTree()
                        ).addi(constraint.bounds[0], constraint.bounds[1], writer)

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
        self, layer_types: List[str]
    ) -> Iterator[WriterContribution]:
        """Attempt to match writers that consume all layers."""

        # First count how many of each distinct type are requested. We'll use
        # this to get candidate writers compatible with the requested count.
        counts = Counter(layer_types)

        def get_candidates(layer_type: Optional[LayerType]) -> Set[WriterContribution]:
            # WriterContributions are hashed based on their command id.
            if not layer_type:
                return set()
            return set(
                map(
                    lambda v: v.data,  # unbox the Interval object
                    self._writers_by_type.get(layer_type, IntervalTree())[
                        counts[layer_type]
                    ],
                )
            )

        types = iter(LayerType)
        candidates = get_candidates(next(types, None))
        for lt in types:
            if candidates:
                candidates &= get_candidates(lt)
            else:
                break

        yield from candidates


def write_layers(
    writer: WriterContribution,
    path: str,
    layer_data: List[Tuple[Any, Dict, str]],
) -> List[Optional[str]]:
    """Write layer data to an svg.

    Parameters
    ----------
    writer : WriterContribution
        Description of the writer to use.
    path : str
        path to file/directory
    layer_data : list of napari.types.LayerData
        List of layer_data, where layer_data is ``(data, meta, layer_type)``.

    Returns
    -------
    path : List of str or None
        If data is successfully written, return the ``path`` that was written.
        Otherwise, if nothing was done, return ``None``.
    """
    if not layer_data:
        return []

    if writer.uses_single_layer_api:
        data, meta, _ = layer_data[0]
        return list(execute_command(writer.command, args=[path, data, meta]))
    else:
        return execute_command(writer.command, args=[path, layer_data])


_GLOBAL_PM = None


def __getattr__(name):
    if name == "plugin_manager":
        global _GLOBAL_PM
        if _GLOBAL_PM is None:
            try:
                _GLOBAL_PM = PluginManager()
            except Exception as e:
                warn(f"Failed to initialize plugin manager: {e}")
                raise
        return _GLOBAL_PM
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
