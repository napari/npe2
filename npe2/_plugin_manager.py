from __future__ import annotations

import os
import warnings
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from psygnal import Signal, SignalGroup

from ._command_registry import CommandRegistry
from .manifest import PluginManifest
from .manifest.writers import LayerType, WriterContribution
from .types import PathLike, PythonName

if TYPE_CHECKING:
    from .manifest.commands import CommandContribution
    from .manifest.menus import MenuItem
    from .manifest.readers import ReaderContribution
    from .manifest.sample_data import SampleDataContribution
    from .manifest.submenu import SubmenuContribution
    from .manifest.themes import ThemeContribution
    from .manifest.widgets import WidgetContribution

__all__ = ["PluginContext", "PluginManager"]
PluginName = str  # this is `PluginManifest.name`

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


class _ContributionsIndex:
    def __init__(self) -> None:
        self._indexed: Set[str] = set()
        self._commands: Dict[str, Tuple[CommandContribution, PluginName]] = {}
        self._readers: List[Tuple[str, ReaderContribution]] = list()
        self._writers: List[Tuple[LayerType, int, int, WriterContribution]] = list()

        # DEPRECATED: only here for napari <= 0.4.15 compat.
        self._samples: DefaultDict[str, List[SampleDataContribution]] = DefaultDict(
            list
        )

    def index_contributions(self, manifest: PluginManifest):
        ctrb = manifest.contributions
        if not ctrb or manifest.name in self._indexed:
            return  # pragma: no cover

        self._indexed.add(manifest.name)
        for cmd in ctrb.commands or ():
            self._commands[cmd.id] = cmd, manifest.name
        for reader in ctrb.readers or ():
            for pattern in reader.filename_patterns:
                self._readers.append((pattern, reader))
            if reader.accepts_directories:
                self._readers.append(("", reader))
        for writer in ctrb.writers or ():
            for c in writer.layer_type_constraints():
                self._writers.append((c.layer_type, *c.bounds, writer))

        # DEPRECATED: only here for napari <= 0.4.15 compat.
        if ctrb.sample_data:
            self._samples[manifest.name] = ctrb.sample_data

    def remove_contributions(self, key: PluginName) -> None:
        """This must completely remove everything added by `index_contributions`."""
        if key not in self._indexed:
            return  # pragma: no cover

        for cmd_id, (_, plugin) in list(self._commands.items()):
            if key == plugin:
                del self._commands[cmd_id]

        self._readers = [
            (pattern, reader)
            for pattern, reader in self._readers
            if reader.plugin_name != key
        ]

        self._writers = [
            (layer_type, min_, max_, writer)
            for layer_type, min_, max_, writer in self._writers
            if writer.plugin_name != key
        ]

        self._indexed.remove(key)

        # DEPRECATED: only here for napari <= 0.4.15 compat.
        self._samples.pop(key, None)

    def get_command(self, command_id: str) -> CommandContribution:
        return self._commands[command_id][0]

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
        path = str(path)

        if os.path.isdir(path):
            yield from (r for pattern, r in self._readers if pattern == "")
        else:
            # not sure about the set logic as it won't be lazy anymore,
            # but would we yield duplicate anymore.
            # above does not have have the unseen check either.
            # it's easy to make an iterable version if we wish, or use more-itertools.
            yield from {r for pattern, r in self._readers if fnmatch(path, pattern)}

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
                w
                for layer, min_, max_, w in self._writers
                if layer == lt and (min_ <= counts[lt] < max_)
            }

        candidates = {w for _, _, _, w in self._writers}
        for lt in LayerType:
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


class PluginManagerEvents(SignalGroup):
    plugins_registered = Signal(
        set,
        description="Emitted with a set of PluginManifest instances "
        "whenever new plugins are registered. 'Registered' means that a "
        "manifest has been provided or discovered.",
    )
    activation_changed = Signal(
        set,
        set,
        description="Emitted with two arguments: a set of plugin "
        "names that were activated, and a set of names that were "
        "deactivated. 'Activated' means the plugin has been *imported*, its "
        "`on_activate` function was called.",
    )
    enablement_changed = Signal(
        set,
        set,
        description="Emitted with two arguments: a set of plugin names "
        "that were enabled, and a set of names that were "
        "disabled. 'Disabled' means the plugin remains installed, but it "
        "cannot be activated, and its contributions will not be indexed.",
    )


class PluginManager:
    __instance: Optional[PluginManager] = None  # a global instance
    _contrib: _ContributionsIndex
    events: PluginManagerEvents

    def __init__(
        self, *, disable: Iterable[str] = (), reg: Optional[CommandRegistry] = None
    ) -> None:
        self._disabled_plugins: Set[PluginName] = set(disable)
        self._command_registry = reg or CommandRegistry()
        self._contexts: Dict[PluginName, PluginContext] = {}
        self._contrib = _ContributionsIndex()
        self._manifests: Dict[PluginName, PluginManifest] = {}
        self.events = PluginManagerEvents(self)

        # up to napari 0.4.15, discovery happened in the init here
        # so if we're running on an older version of napari, we need to discover
        try:
            nv = metadata.version("napari")
        except metadata.PackageNotFoundError:  # pragma: no cover
            pass
        else:  # pragma: no cover
            vsplit = nv.split(".")[:4]
            if (
                "dev" in nv
                and vsplit < ["0", "4", "16", "dev4"]
                or "dev" not in nv
                and vsplit < ["0", "4", "16"]
            ):
                self.discover()

    @classmethod
    def instance(cls) -> PluginManager:
        """Singleton instance."""
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @property
    def commands(self) -> CommandRegistry:
        return self._command_registry

    # Discovery, activation, enablement

    def discover(self, paths: Sequence[str] = (), clear=False) -> None:
        """Discover and index plugin manifests in the environment.

        Parameters
        ----------
        paths : Sequence[str]
            Optional list of strings to insert at front of sys.path when
            discovering.
        clear : bool
            Clear and re-index the environment.  If `False` (the default),
            calling discover again will only register and index newly
            discovered plugins. (Existing manifests will not be re-indexed)
        """
        if clear:
            self._contrib = _ContributionsIndex()
            self._manifests.clear()

        with self.events.plugins_registered.paused(lambda a, b: (a[0] | b[0],)):
            for result in PluginManifest.discover(paths=paths):
                if result.manifest and result.manifest.name not in self._manifests:
                    self.register(result.manifest, warn_disabled=False)

    def register(self, manifest: PluginManifest, warn_disabled=True) -> None:
        """Register a plugin manifest"""
        if manifest.name in self._manifests:
            raise ValueError(f"A manifest with name {manifest.name!r} already exists.")

        self._manifests[manifest.name] = manifest
        if self.is_disabled(manifest.name):
            if warn_disabled:
                warnings.warn(
                    f"Disabled plugin {manifest.name!r} was registered, but will not "
                    "be indexed. Use `warn_disabled=False` to suppress this message."
                )
        else:
            self._contrib.index_contributions(manifest)
        self.events.plugins_registered.emit({manifest})

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
        if key not in self._manifests:
            raise KeyError(f"Cannot activate unrecognized plugin: {key!r}")

        if self.is_disabled(key):
            raise ValueError(f"Cannot activate disabled plugin: {key!r}")

        # create the context that will be with this plugin for its lifetime.
        ctx = self.get_context(key)
        if ctx._activated:
            # prevent "reactivation"
            return ctx

        mf = self._manifests[key]
        try:
            if mf.on_activate:
                _call_python_name(mf.on_activate, args=(ctx,))
        except Exception as e:  # pragma: no cover
            self._contexts.pop(key, None)
            raise type(e)(f"Activating plugin {key!r} failed: {e}") from e

        if mf.contributions and mf.contributions.commands:
            for cmd in mf.contributions.commands:
                if cmd.python_name and cmd.id not in self.commands:
                    self.commands.register(cmd.id, cmd.python_name)

        ctx._activated = True
        self.events.activation_changed({mf.name}, {})
        return ctx

    def get_context(self, plugin_name: PluginName) -> PluginContext:
        """Return PluginContext for plugin_name"""
        if plugin_name not in self._contexts:
            self._contexts[plugin_name] = PluginContext(plugin_name, reg=self.commands)
        return self._contexts[plugin_name]

    def deactivate(self, plugin_name: PluginName) -> None:
        """Call the plugin's `on_deactivate` function."""
        if plugin_name not in self._contexts:
            return
        mf = self._manifests[plugin_name]
        ctx = self._contexts.pop(plugin_name)
        if mf.on_deactivate:
            _call_python_name(mf.on_deactivate, args=(ctx,))
        ctx._activated = False
        ctx._dispose()
        self.events.activation_changed({}, {mf.name})

    def enable(self, plugin_name: PluginName) -> None:
        """Enable a plugin (which mostly means just `un-disable` it.

        This is a no-op if the plugin wasn't already disabled.
        """
        if not self.is_disabled(plugin_name):
            return  # pragma: no cover

        self._disabled_plugins.remove(plugin_name)
        mf = self._manifests.get(plugin_name)
        if mf is not None:
            self._contrib.index_contributions(mf)
        self.events.enablement_changed({plugin_name}, {})

    def disable(self, plugin_name: PluginName) -> None:
        """Disable a plugin"""
        self._disabled_plugins.add(plugin_name)
        self._contrib.remove_contributions(plugin_name)
        self.events.enablement_changed({}, {plugin_name})

    def is_disabled(self, plugin_name: str) -> bool:
        """Return `True` if plugin_name is disabled."""
        return plugin_name in self._disabled_plugins

    # Getting manifests

    def get_manifest(self, plugin_name: str) -> PluginManifest:
        """Gen manifest for `plugin_name`"""
        key = str(plugin_name).split(".")[0]
        try:
            return self._manifests[key]
        except KeyError as e:
            msg = f"Manifest key {key!r} not found in {list(self._manifests)}"
            raise KeyError(msg) from e

    def iter_manifests(
        self, disabled: Optional[bool] = None
    ) -> Iterator[PluginManifest]:
        """Iterate through registered manifests.

        Parameters
        ----------
        disabled : Optional[bool]
            If `False`, yield only enabled manifests.  If `True`, yield only disabled
            manifests.  If `None` (the default), yield all manifests.

        Yields
        ------
        PluginManifest
        """
        for key, mf in self._manifests.items():
            if disabled is True and not self.is_disabled(key):
                continue
            elif disabled is False and self.is_disabled(key):
                continue
            yield mf

    def __contains__(self, name: str) -> bool:
        return name in self._manifests

    def __getitem__(self, name: str) -> PluginManifest:
        return self.get_manifest(name)

    # Accessing Contributions

    def get_command(self, command_id: str) -> CommandContribution:
        return self._contrib.get_command(command_id)

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        for mf in self.iter_manifests(disabled=False):
            for subm in mf.contributions.submenus or ():
                if submenu_id == subm.id:
                    return subm
        raise KeyError(f"No plugin provides a submenu with id {submenu_id}")

    def iter_menu(self, menu_key: str) -> Iterator[MenuItem]:
        for mf in self.iter_manifests(disabled=False):
            yield from getattr(mf.contributions.menus, menu_key, ())

    def iter_themes(self) -> Iterator[ThemeContribution]:
        for mf in self.iter_manifests(disabled=False):
            yield from mf.contributions.themes or ()

    def iter_compatible_readers(
        self, path: Union[PathLike, List[PathLike]]
    ) -> Iterator[ReaderContribution]:
        return self._contrib.iter_compatible_readers(path)

    def iter_compatible_writers(
        self, layer_types: Sequence[str]
    ) -> Iterator[WriterContribution]:
        return self._contrib.iter_compatible_writers(layer_types)

    def iter_widgets(self) -> Iterator[WidgetContribution]:
        for mf in self.iter_manifests(disabled=False):
            yield from mf.contributions.widgets or ()

    def iter_sample_data(
        self,
    ) -> Iterator[Tuple[PluginName, List[SampleDataContribution]]]:
        """Iterates over (plugin_name, [sample_contribs])."""
        for mf in self.iter_manifests(disabled=False):
            if mf.contributions.sample_data:
                yield mf.name, mf.contributions.sample_data

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
