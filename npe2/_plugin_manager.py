from __future__ import annotations

import os
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from intervaltree import IntervalTree

from ._command_registry import CommandRegistry
from .manifest import PluginManifest
from .manifest.writers import LayerType, WriterContribution
from .types import PathLike, PythonName

if TYPE_CHECKING:
    from .manifest.commands import CommandContribution
    from .manifest.contributions import ContributionPoints
    from .manifest.menus import MenuItem
    from .manifest.readers import ReaderContribution
    from .manifest.sample_data import SampleDataContribution
    from .manifest.submenu import SubmenuContribution
    from .manifest.themes import ThemeContribution
    from .manifest.widgets import WidgetContribution

    T = TypeVar("T")

    class Interval(tuple, Generic[T]):
        begin: int
        end: int
        data: T

    class TypedIntervalTree(IntervalTree, Generic[T]):
        def addi(self, begin: int, end: int, data: T) -> None:
            ...

        def __getitem__(self, index: Union[int, slice]) -> Set[Interval[T]]:
            ...


__all__ = ["PluginContext", "PluginManager"]
PluginName = str  # this is `PluginManifest.name`


class _ContributionsIndex:
    def __init__(self) -> None:
        self._submenus: Dict[str, SubmenuContribution] = {}
        self._commands: Dict[str, Tuple[CommandContribution, PluginName]] = {}
        self._themes: Dict[str, ThemeContribution] = {}
        self._widgets: List[WidgetContribution] = []
        self._readers: DefaultDict[str, List[ReaderContribution]] = DefaultDict(list)
        self._samples: DefaultDict[str, List[SampleDataContribution]] = DefaultDict(
            list
        )
        self._writers_by_type: DefaultDict[
            LayerType, TypedIntervalTree[WriterContribution]
        ] = DefaultDict(IntervalTree)
        self._writers_by_command: DefaultDict[
            str, List[WriterContribution]
        ] = DefaultDict(list)

    def index_contributions(self, ctrb: ContributionPoints, key: PluginName):
        if ctrb.sample_data:
            self._samples[key] = ctrb.sample_data
        for cmd in ctrb.commands or []:
            self._commands[cmd.id] = cmd, key
        for subm in ctrb.submenus or []:
            self._submenus[subm.id] = subm
        for theme in ctrb.themes or []:
            self._themes[theme.id] = theme
        self._widgets.extend(ctrb.widgets or [])
        for reader in ctrb.readers or []:
            for pattern in reader.filename_patterns:
                self._readers[pattern].append(reader)
            if reader.accepts_directories:
                self._readers[""].append(reader)
        for writer in ctrb.writers or []:
            self._writers_by_command[writer.command].append(writer)
            for c in writer.layer_type_constraints():
                self._writers_by_type[c.layer_type].addi(*c.bounds, writer)


class PluginManager:
    __instance: Optional[PluginManager] = None  # a global instance
    _contrib: _ContributionsIndex

    def __init__(self, reg: Optional[CommandRegistry] = None) -> None:
        self._command_registry = reg or CommandRegistry()
        self._contexts: Dict[PluginName, PluginContext] = {}
        self._manifests: Dict[PluginName, PluginManifest] = {}
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
            if result.manifest and result.manifest.name not in self._manifests:
                self.register(result.manifest)

    def register(self, manifest: PluginManifest) -> None:
        if manifest.name in self._manifests:
            raise ValueError(f"A manifest with name {manifest.name!r} already exists.")
        self._manifests[manifest.name] = manifest
        if manifest.contributions:
            self._contrib.index_contributions(manifest.contributions, manifest.name)

    def get_manifest(self, key: str) -> PluginManifest:
        key = str(key).split(".")[0]
        try:
            return self._manifests[key]
        except KeyError:
            raise KeyError(f"Manifest key {key!r} not found in {list(self._manifests)}")

    def get_command(self, command_id: str) -> CommandContribution:
        return self._contrib._commands[command_id][0]

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        return self._contrib._submenus[submenu_id]

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self._manifests.values():
            if mf.contributions:
                yield from getattr(mf.contributions.menus, menu_key, [])

    def iter_themes(self) -> Iterator[ThemeContribution]:
        yield from self._contrib._themes.values()

    def activate(self, key: PluginName) -> PluginContext:
        """Activate plugin with `key`.

        This does the following:
            - finds the manifest for the associated plugin key
            - gets or creates a PluginContext for the plugin
            - bails if it's already activated
            - otherwise calls the plugin's activate() function, passing the Context.
            - imports any commands that were declared as python_name:
        """
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
            if mf.on_activate:
                _call_python_name(mf.on_activate, args=(ctx,))
                ctx._activated = True
        except Exception as e:  # pragma: no cover
            self._contexts.pop(key, None)
            raise type(e)(f"Activating plugin {key!r} failed: {e}") from e

        if mf.contributions and mf.contributions.commands:
            for cmd in mf.contributions.commands:
                if cmd.python_name and cmd.id not in self.commands:
                    self.commands.register(cmd.id, cmd.python_name)

        return ctx

    def deactivate(self, key: PluginName) -> None:
        if key not in self._contexts:
            return
        mf = self._manifests[key]
        ctx = self._contexts.pop(key)
        if mf.on_deactivate:
            _call_python_name(mf.on_deactivate, args=(ctx,))
            ctx._activated = False
        ctx._dispose()

    def iter_compatible_readers(
        self, path: Union[PathLike, List[PathLike]]
    ) -> Iterator[ReaderContribution]:
        if not path:
            return

        if isinstance(path, list):
            if len({Path(i).suffix for i in path}) > 1:
                raise ValueError(
                    "All paths in the stack list must have the same extension."
                )
            path = path[0]

        if os.path.isdir(path):
            yield from self._contrib._readers[""]
        else:
            seen: Set[str] = set()
            for ext, readers in self._contrib._readers.items():
                if ext and fnmatch(str(path), ext):
                    for r in readers:
                        if r.command not in seen:
                            seen.add(r.command)
                            yield r

    @classmethod
    def instance(cls) -> PluginManager:
        """Singleton instance."""
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def get_context(self, plugin_key: PluginName) -> PluginContext:
        if plugin_key not in self._contexts:
            self._contexts[plugin_key] = PluginContext(plugin_key, reg=self.commands)
        return self._contexts[plugin_key]

    def iter_sample_data(self) -> Iterator[Tuple[str, List[SampleDataContribution]]]:
        """Iterates over (plugin_name, [sample_contribs])."""
        yield from self._contrib._samples.items()

    def iter_widgets(self) -> Iterator[WidgetContribution]:
        yield from self._contrib._widgets

    def iter_compatible_writers(
        self, layer_types: Sequence[str]
    ) -> Iterator[WriterContribution]:
        """Attempt to match writers that consume all layers."""

        if not layer_types:
            return

        # First count how many of each distinct type are requested. We'll use
        # this to get candidate writers compatible with the requested count.
        counts = Counter(layer_types)

        def _get_candidates(lt: LayerType) -> Set[WriterContribution]:
            return {
                v.data for v in self._contrib._writers_by_type[lt][counts[lt]] or []
            }

        types = iter(LayerType)
        candidates = _get_candidates(next(types))
        for lt in types:
            if candidates:
                candidates &= _get_candidates(lt)
            else:
                break

        def _writer_key(writer: WriterContribution) -> Tuple[bool, int, int, List[str]]:
            # 1. writers with no file extensions (like directory writers) go last
            no_ext = len(writer.filename_extensions) == 0

            # 2. more "specific" writers first
            nbounds = sum(not c.is_zero() for c in writer.layer_type_constraints())

            # 3. then sort by the number of listed extensions
            #    (empty set of extensions goes last)
            ext_len = len(writer.filename_extensions)

            # 4. finally group related extensions together
            exts = writer.filename_extensions
            return (no_ext, nbounds, ext_len, exts)

        yield from sorted(
            candidates,
            key=_writer_key,
        )

    def get_writer(
        self, path: str, layer_types: Sequence[str], plugin_name: Optional[str] = None
    ) -> Tuple[Optional[WriterContribution], str]:
        """Get Writer contribution appropriate for `path`, and `layer_types`.

        When `path` has a file extension, find a compatible writer that has
        that same extension. When there is no extension and only a single layer,
        find a compatible writer and append the extension.
        Otherwise, find a compatible no-extension writer and write to that.
        No-extension writers typically write to a folder.

        Parameters
        ----------
        path : str
            Path to write
        layer_types : Sequence[str]
            Sequence of layer type strings (e.g. ['image', 'labels'])
        plugin_name : Optional[str], optional
            Name of plugin to use. If provided, only writers from `plugin_name` will be
            considered, otherwise all plugins are considered. by default `None`.

        Returns
        -------
        Tuple[Optional[WriterContribution], str]
            WriterContribution and path that will be written.
        """
        ext = Path(path).suffix.lower() if path else ""

        for writer in self.iter_compatible_writers(layer_types):
            if not plugin_name or writer.command.startswith(plugin_name):
                if (
                    ext
                    and ext in writer.filename_extensions
                    or not ext
                    and len(layer_types) != 1
                    and not writer.filename_extensions
                ):
                    return writer, path
                elif not ext and len(layer_types) == 1:  # No extension, single layer.
                    ext = next(iter(writer.filename_extensions), "")
                    return writer, path + ext
                # When the list of extensions for the writer doesn't match the
                # extension in the filename, keep searching.

        # Nothing got found
        return None, path


class PluginContext:
    """An object that can contain information for a plugin over its lifetime."""

    # stores all created contexts (currently cleared by `PluginManager.deactivate`)

    def __init__(
        self, plugin_key: PluginName, reg: Optional[CommandRegistry] = None
    ) -> None:
        self._activated = False
        self.plugin_key = plugin_key
        self._command_registry = reg or PluginManager.instance().commands
        self._imports: Set[str] = set()  # modules that were imported by this plugin
        self._disposables: Set[Callable] = set()  # functions to call when deactivating

    def _dispose(self):
        for dispose in self._disposables:
            dispose()

    def register_command(self, id: str, command: Optional[Callable] = None):
        def _inner(command):
            self._disposables.add(self._command_registry.register(id, command))
            return command

        return _inner if command is None else _inner(command)


def _call_python_name(python_name: PythonName, args=()) -> Any:
    """convenience to call `python_name` function. eg `module.submodule:funcname`."""
    from .manifest.utils import import_python_name

    if not python_name:  # pragma: no cover
        return None

    func = import_python_name(python_name)
    if callable(func):
        return func(*args)
