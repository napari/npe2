from __future__ import annotations

import contextlib
import os
import urllib
import warnings
from collections import Counter, defaultdict
from fnmatch import fnmatch
from importlib import metadata
from logging import getLogger
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from psygnal import Signal, SignalGroup

from ._command_registry import CommandRegistry
from .manifest import PluginManifest
from .manifest._npe1_adapter import NPE1Adapter
from .manifest.contributions import LayerType, WriterContribution
from .types import PathLike, PythonName

if TYPE_CHECKING:
    from .manifest.contributions import (
        CommandContribution,
        MenuCommand,
        MenuItem,
        ReaderContribution,
        SampleDataContribution,
        SubmenuContribution,
        ThemeContribution,
        WidgetContribution,
    )

    IntStr = Union[int, str]
    AbstractSetIntStr = AbstractSet[IntStr]
    DictIntStrAny = Dict[IntStr, Any]
    MappingIntStrAny = Mapping[IntStr, Any]
    InclusionSet = Union[AbstractSetIntStr, MappingIntStrAny, None]
    DisposeFunction = Callable[[], None]

logger = getLogger(__name__)

__all__ = ["PluginContext", "PluginManager"]
PluginName = str  # this is `PluginManifest.name`


class _ContributionsIndex:
    def __init__(self) -> None:
        self._indexed: Set[str] = set()
        self._commands: Dict[str, Tuple[CommandContribution, PluginName]] = {}
        self._readers: List[Tuple[str, ReaderContribution]] = []
        self._writers: List[Tuple[LayerType, int, int, WriterContribution]] = []

        # DEPRECATED: only here for napari <= 0.4.15 compat.
        self._samples: DefaultDict[str, List[SampleDataContribution]] = DefaultDict(
            list
        )

    def reindex(self, manifest):
        self.remove_contributions(manifest.name)
        self.index_contributions(manifest)

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

    def iter_compatible_readers(self, paths: List[str]) -> Iterator[ReaderContribution]:
        assert isinstance(paths, list)
        if not paths:
            return  # pragma: no cover

        if len({Path(i).suffix for i in paths}) > 1:
            raise ValueError(
                "All paths in the stack list must have the same extension."
            )
        path = paths[0]
        if not path:
            return
        assert isinstance(path, str)

        if os.path.isdir(path):
            yield from (r for pattern, r in self._readers if pattern == "")
        else:
            # ensure not a URI
            if not urllib.parse.urlparse(path).scheme:
                # lower case the extension for checking manifest pattern
                base = os.path.splitext(Path(path).stem)[0]
                ext = "".join(Path(path).suffixes)
                path = base + ext.lower()
            # not sure about the set logic as it won't be lazy anymore,
            # but would we yield duplicate anymore.
            # above does not have have the unseen check either.
            # it's easy to make an iterable version if we wish, or use more-itertools.
            # match against pattern.lower() to make matching case insensitive
            yield from {
                r for pattern, r in self._readers if fnmatch(path, pattern.lower())
            }

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

        # keep ordered without duplicates
        candidates = list({w: None for _, _, _, w in self._writers})
        for lt in LayerType:
            if candidates:
                candidates = [i for i in candidates if i in _get_candidates(lt)]
            else:
                break

        def _writer_key(writer: WriterContribution) -> Tuple[bool, int]:
            # 1. writers with no file extensions (like directory writers) go last
            no_ext = len(writer.filename_extensions) == 0

            # 2. more "specific" writers first
            nbounds = sum(not c.is_zero() for c in writer.layer_type_constraints())
            return (no_ext, nbounds)

        yield from sorted(candidates, key=_writer_key)


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
        self._npe1_adapters: List[NPE1Adapter] = []
        self._command_menu_map: Dict[
            str, Dict[str, Dict[str, List[MenuCommand]]]
        ] = defaultdict(dict)

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
        """Return global PluginManager singleton instance."""
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @property
    def commands(self) -> CommandRegistry:
        return self._command_registry

    # Discovery, activation, enablement

    def discover(
        self, paths: Sequence[str] = (), clear=False, include_npe1=False
    ) -> int:
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
        include_npe1 : bool
            Whether to detect npe1 plugins as npe1_adapters during discovery.
            By default `False`.

        Returns
        -------
        discover_count : int
            Number of discovered plugins

        """
        if clear:
            self._contrib = _ContributionsIndex()
            self._manifests.clear()

        count = 0

        with self.events.plugins_registered.paused(lambda a, b: (a[0] | b[0],)):
            for result in PluginManifest.discover(paths=paths):
                if (
                    result.manifest
                    and result.manifest.name not in self._manifests
                    and (include_npe1 or not isinstance(result.manifest, NPE1Adapter))
                ):
                    self.register(result.manifest, warn_disabled=False)
                    count += 1
        return count

    def index_npe1_adapters(self):
        """Import and index any/all npe1 adapters."""
        with warnings.catch_warnings():
            warnings.showwarning = lambda e, *_: print(str(e).split(" Please add")[0])
            while self._npe1_adapters:
                self._contrib.index_contributions(self._npe1_adapters.pop())

    def register(
        self, manifest_or_package: Union[PluginManifest, str], warn_disabled=True
    ) -> None:
        """Register a plugin manifest, path to manifest file, or a package name.

        Parameters
        ----------
        manifest_or_package : Union[PluginManifest, str]
            Either a PluginManifest instance or a string. If a string, should be either
            the name of a plugin package, or a path to a plugin manifest file.
        warn_disabled : bool, optional
            If True, emits a warning if the plugin being registered is marked as
            disabled, by default True.

        Raises
        ------
        ValueError
            If a plugin with the same name is already registered.
        """
        if isinstance(manifest_or_package, str):
            if Path(manifest_or_package).is_file():
                manifest = PluginManifest.from_file(manifest_or_package)
            else:
                manifest = PluginManifest.from_distribution(manifest_or_package)
        elif isinstance(manifest_or_package, PluginManifest):
            manifest = manifest_or_package
        else:  # pragma: no cover
            raise TypeError(
                "The first argument to register must be a string or a PluginManifest."
            )
        if manifest.name in self._manifests:
            raise ValueError(f"A manifest with name {manifest.name!r} already exists.")

        self._manifests[manifest.name] = manifest
        if self.is_disabled(manifest.name):
            if warn_disabled:
                warnings.warn(
                    f"Disabled plugin {manifest.name!r} was registered, but will not "
                    "be indexed. Use `warn_disabled=False` to suppress this message.",
                    stacklevel=2,
                )
        elif isinstance(manifest, NPE1Adapter):
            self._npe1_adapters.append(manifest)
        else:
            self._contrib.index_contributions(manifest)
            self._populate_command_menu_map(manifest)
        self.events.plugins_registered.emit({manifest})

    def _populate_command_menu_map(self, manifest: PluginManifest):
        # map of manifest -> command -> menu_id -> list[items]
        self._command_menu_map[manifest.name] = defaultdict(lambda: defaultdict(list))
        menu_map = self._command_menu_map[manifest.name]  # just for conciseness below
        for menu_id, menu_items in manifest.contributions.menus.items() or ():
            # command IDs are keys in map
            # each value is a dict menu_id: list of MenuCommands
            # for the command and menu
            for item in menu_items:
                if (command_id := getattr(item, "command", None)) is not None:
                    menu_map[command_id][menu_id].append(item)

    def unregister(self, key: PluginName):
        """Unregister plugin named `key`."""
        if key not in self._manifests:
            raise ValueError(f"No registered plugin named {key!r}")  # pragma: no cover
        self.deactivate(key)
        self._contrib.remove_contributions(key)
        self._command_menu_map.pop(key)
        self._manifests.pop(key)

    def activate(self, key: PluginName) -> PluginContext:
        """Activate plugin with `key`.

        This does the following:
            - finds the manifest for the associated plugin key
            - gets or creates a PluginContext for the plugin
            - bails if it's already activated
            - otherwise calls the plugin's activate() function, passing the Context.
            - imports any commands that were declared as python_name:
            - emits an event
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

        self.commands.register_manifest(mf)
        ctx._activated = True
        self.events.activation_changed({mf.name}, {})
        return ctx

    def get_context(self, plugin_name: PluginName) -> PluginContext:
        """Return PluginContext for plugin_name"""
        if plugin_name not in self._contexts:
            self._contexts[plugin_name] = PluginContext(plugin_name, reg=self.commands)
        return self._contexts[plugin_name]

    def deactivate(self, plugin_name: PluginName) -> None:
        """Deactivate `plugin_name`

        This does the following:
            - unregisters all commands from the associated manifest
            - calls the plugin's on_deactivate() func, passing the Context.
            - calls and cleanup functions in the context's `_dispose` method.
            - emits an event

        This does not:
            - "unindex" contributions (i.e. the contributions of a deactivated plugin
              are still visible in the index)
            - "disable" the plugin (i.e. it can still be used).
        """
        mf = self._manifests[plugin_name]
        self.commands.unregister_manifest(mf)
        if plugin_name not in self._contexts:
            return
        ctx = self._contexts.pop(plugin_name)
        if mf.on_deactivate:
            _call_python_name(mf.on_deactivate, args=(ctx,))
        ctx._activated = False
        ctx._dispose()
        self.events.activation_changed({}, {mf.name})

    def enable(self, plugin_name: PluginName) -> None:
        """Enable a plugin (which mostly means just `un-disable` it).

        This is a no-op if the plugin wasn't already disabled.
        """
        if not self.is_disabled(plugin_name):
            return  # pragma: no cover

        self._disabled_plugins.remove(plugin_name)
        mf = self._manifests.get(plugin_name)
        if mf is not None:
            self._contrib.index_contributions(mf)
            self._populate_command_menu_map(mf)
        self.events.enablement_changed({plugin_name}, {})

    def disable(self, plugin_name: PluginName) -> None:
        """Disable a plugin.

        'Disabled' means the plugin remains installed, but it cannot be activated,
        and its contributions will not be indexed.  Menu items and keybindings and
        such will not be available.

        In napari, plugin disablement is persisted across sessions.
        """
        if self.is_disabled(plugin_name):
            return  # pragma: no cover

        with contextlib.suppress(KeyError):
            self.deactivate(plugin_name)

        self._disabled_plugins.add(plugin_name)
        self._contrib.remove_contributions(plugin_name)
        self._command_menu_map.pop(plugin_name, None)
        self.events.enablement_changed({}, {plugin_name})

    def is_disabled(self, plugin_name: str) -> bool:
        """Return `True` if plugin_name is disabled."""
        return plugin_name in self._disabled_plugins

    # Getting manifests

    def get_manifest(self, plugin_name: str) -> PluginManifest:
        """Get manifest for `plugin_name`"""
        key = str(plugin_name).split(".")[0]
        if key not in self._manifests:
            msg = f"Manifest key {key!r} not found in {list(self._manifests)}"
            raise KeyError(msg)
        return self._manifests[key]

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

    def dict(
        self,
        *,
        include: Optional[InclusionSet] = None,
        exclude: Optional[InclusionSet] = None,
    ) -> Dict[str, Any]:
        """Return a dictionary with the state of the plugin manager.

        `include` and `exclude` will be passed to each `PluginManifest.dict()`
        See pydantic documentation for details:
        https://pydantic-docs.helpmanual.io/usage/exporting_models/#modeldict

        `include` and `exclude` may be a set of dotted strings, indicating
        nested fields in the manifest model.  For example:

            {'contributions.readers', 'package_metadata.description'}

        will be expanded to

            {
                'contributions': {'readers': True},
                'package_metadata': {'description': True}
            }

        This facilitates selection of nested fields on the command line.


        Parameters
        ----------
        include : InclusionSet, optional
            A set of manifest fields to include, by default all fields are included.
        exclude : InclusionSet, optional
            A set of manifest fields to exclude, by default no fields are excluded.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the state of the plugin manager.  Keys will include

                - `'plugins'`: dict of `{name: manifest.dict()} for discovered plugins
                - `'disabled'`: set of disabled plugins
                - `'activated'`: set of activated plugins

        """
        # _include =
        out: Dict[str, Any] = {
            "plugins": {
                mf.name: mf.dict(
                    include=_expand_dotted_set(include),
                    exclude=_expand_dotted_set(exclude),
                )
                for mf in self.iter_manifests()
            }
        }
        if not exclude or "disabled" not in exclude:
            out["disabled"] = set(self._disabled_plugins)
        if not exclude or "activated" not in exclude:
            out["activated"] = {
                name for name, ctx in self._contexts.items() if ctx._activated
            }
        return out

    def __contains__(self, name: str) -> bool:
        return name in self._manifests

    def __getitem__(self, name: str) -> PluginManifest:
        return self.get_manifest(name)

    def __len__(self) -> int:
        return len(self._manifests)

    # Accessing Contributions

    def get_command(self, command_id: str) -> CommandContribution:
        """Retrieve CommandContribution for `command_id`"""
        return self._contrib.get_command(command_id)

    def get_submenu(self, submenu_id: str) -> SubmenuContribution:
        """Get SubmenuContribution for `submenu_id`."""
        for mf in self.iter_manifests(disabled=False):
            for subm in mf.contributions.submenus or ():
                if submenu_id == subm.id:
                    return subm
        raise KeyError(f"No plugin provides a submenu with id {submenu_id}")

    def iter_menu(self, menu_key: str, disabled=False) -> Iterator[MenuItem]:
        """Iterate over `MenuItems` in menu with id `menu_key`."""
        for mf in self.iter_manifests(disabled=disabled):
            yield from mf.contributions.menus.get(menu_key, ())

    def menus(self, disabled=False) -> Dict[str, List[MenuItem]]:
        """Return all registered menu_key -> List[MenuItems]."""
        _menus: DefaultDict[str, List[MenuItem]] = DefaultDict(list)
        for mf in self.iter_manifests(disabled=disabled):
            for key, menus in mf.contributions.menus.items():
                _menus[key].extend(menus)
        return dict(_menus)

    def iter_themes(self) -> Iterator[ThemeContribution]:
        """Iterate over discovered/enuabled `ThemeContributions`."""
        for mf in self.iter_manifests(disabled=False):
            yield from mf.contributions.themes or ()

    def iter_compatible_readers(
        self, path: Union[PathLike, Sequence[str]]
    ) -> Iterator[ReaderContribution]:
        """Iterate over ReaderContributions compatible with `path`.

        Parameters
        ----------
        path : Union[PathLike, Sequence[str]]
            Pathlike or list of pathlikes, with file(s) to read.
        """
        if isinstance(path, (str, Path)):
            path = [path]
        assert isinstance(path, list)
        return self._contrib.iter_compatible_readers(path)

    def iter_compatible_writers(
        self, layer_types: Sequence[str]
    ) -> Iterator[WriterContribution]:
        """Iterate over compatible WriterContributions given a sequence of layer_types.

        Parameters
        ----------
        layer_types : Sequence[str]
            list of lowercase Layer type names like `['image', 'labels']`
        """
        return self._contrib.iter_compatible_writers(layer_types)

    def iter_widgets(self) -> Iterator[WidgetContribution]:
        """Iterate over discovered WidgetContributions."""
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
        # functions to call when deactivating
        self._disposables: Set[DisposeFunction] = set()

    def _dispose(self):
        while self._disposables:
            try:
                self._disposables.pop()()
            except Exception as e:
                logger.warning(f"Error while disposing {self.plugin_key}; {e}")

    def register_command(self, id: str, command: Optional[Callable] = None):
        """Associate a callable with a command id."""

        def _inner(command):
            self._disposables.add(self._command_registry.register(id, command))
            return command

        return _inner if command is None else _inner(command)

    def register_disposable(self, func: DisposeFunction):
        """Register `func` to be executed when this plugin is deactivated."""
        self._disposables.add(func)


def _call_python_name(python_name: PythonName, args=()) -> Any:
    """convenience to call `python_name` function. eg `module.submodule:funcname`."""
    from .manifest.utils import import_python_name

    if not python_name:  # pragma: no cover
        return None

    func = import_python_name(python_name)
    if callable(func):
        return func(*args)


def _expand_dotted_set(inclusion_set: InclusionSet) -> InclusionSet:
    """Expand a set of strings with dots to a dict of dicts.

    Examples
    --------
    >>> _expand_dotted_set({'a.b', 'c', 'a.d'})
    {'a': {'b': True, 'd': True}, 'c': True}

    >>> _expand_dotted_set({'a.b', 'a.d.e', 'a'})
    {'a'}

    >>> _expand_dotted_set({'a.b', 'a.d', 'x.y.z'})
    {'x': {'y': {'z': True}}, 'a': {'d': True, 'b': True}}
    """
    if not isinstance(inclusion_set, set) or all(
        "." not in str(s) for s in inclusion_set
    ):
        return inclusion_set

    result: Dict[IntStr, Any] = {}
    # sort the strings based on the number of dots,
    # so that higher level keys take precedence
    # e.g. {'a.b', 'a.d.e', 'a'} -> {'a'}
    for key in sorted(inclusion_set, key=lambda i: i.count("."), reverse=True):
        if isinstance(key, str):
            parts = key.split(".")
            if len(parts) == 1:
                result[key] = True
            else:
                cur = result
                for part in parts[:-1]:
                    # integer keys are used in pydantic for lists
                    # they must remain integers
                    _p: IntStr = int(part) if part.isdigit() else part
                    cur = cur.setdefault(_p, {})
                cur[parts[-1]] = True

    return result
