from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from npe2._pydantic_compat import BaseModel, ValidationError

from ._plugin_manager import PluginManager
from .manifest.contributions import (
    CommandContribution,
    ContributionPoints,
    ReaderContribution,
    SampleDataGenerator,
    WidgetContribution,
    WriterContribution,
)
from .manifest.schema import PluginManifest

C = TypeVar("C", bound=BaseModel)
T = TypeVar("T", bound=Callable[..., Any])


# a mapping of contribution type to string name in the ContributionPoints
# e.g. {ReaderContribution: 'readers'}
CONTRIB_NAMES = {v.type_: k for k, v in ContributionPoints.__fields__.items()}
for key in list(CONTRIB_NAMES):
    if getattr(key, "__origin__", "") == Union:
        v = CONTRIB_NAMES.pop(key)
        for t in key.__args__:
            CONTRIB_NAMES[t] = v


class DynamicPlugin:
    """A context manager that creates and modifies temporary plugin contributions.

    Parameters
    ----------
    name : str
        Optional name for this temporary plugin., by default "temp-plugin"
    plugin_manager : Optional[PluginManager]
        A plugin manager instance with which to associate this plugin. If `None` (the
        default), the global `PluginManager.instance()` will be used.
    manifest: Optional[PluginManifest],
        Optionally provide a manifest to use for this plugin. If not provided, a new
        manifest will be created.

    Examples
    --------
    >>> with TemporaryPlugin('name') as p:
    >>>     @p.contribute.sample_data
    >>>     def make_data() -> np.ndarray: ...
    """

    def __init__(
        self,
        name: str = "temp-plugin",
        plugin_manager: Optional[PluginManager] = None,
        manifest: Optional[PluginManifest] = None,
    ) -> None:
        if isinstance(manifest, PluginManifest):
            self.manifest = manifest
        else:
            self.manifest = PluginManifest(name=name)
        self.contribute = ContributionDecorators(self)
        self._pm = plugin_manager

    @property
    def name(self) -> str:
        """Name of the plugin."""
        return self.manifest.name

    @property
    def display_name(self) -> str:
        """Display name of the plugin."""
        return self.manifest.display_name

    def cleanup(self) -> None:
        """Remove this plugin from its plugin manager."""
        self.plugin_manager.unregister(self.manifest.name)

    def register(self) -> None:
        """Register this plugin with its plugin manager."""
        self.plugin_manager.register(self.manifest)

    def clear(self) -> None:
        """Clear contributions."""
        self.plugin_manager.deactivate(self.manifest.name)
        self.plugin_manager._contrib.remove_contributions(self.manifest.name)
        self.manifest.contributions = ContributionPoints()

    @property
    def plugin_manager(self) -> PluginManager:
        """Return the plugin manager this plugin is registered in.

        If unset, will use the global plugin manager instance.
        """
        return self._pm if self._pm is not None else PluginManager.instance()

    @plugin_manager.setter
    def plugin_manager(self, pm: Optional[PluginManager]) -> None:
        """Set the plugin manager this plugin is registered in."""
        if pm is self._pm:  # pragma: no cover
            return

        my_cmds: Dict[str, Callable] = {
            k: v.function
            for k, v in self.plugin_manager.commands._commands.items()
            if k.startswith(self.manifest.name) and v.function
        }
        self.cleanup()
        self._pm = pm
        self.register()
        for k, v in my_cmds.items():
            self.plugin_manager.commands.register(k, v)

    def __enter__(self) -> DynamicPlugin:
        self.register()
        return self

    def __exit__(self, *_) -> None:
        self.cleanup()

    def spawn(
        self,
        name: Optional[str] = None,
        plugin_manager: Optional[PluginManager] = None,
        register: bool = False,
    ) -> DynamicPlugin:
        """Create a new DynamicPlugin instance with the same plugin manager.

        Parameters
        ----------
        name : Optional[str]
            If not provided, will increment current name, by default None
        plugin_manager : Optional[PluginManager]
            Plugin manager, by default the same as this plugin's plugin manager
        register : bool
            Whether to register the new plugin, by default False

        Returns
        -------
        DynamicPlugin
            A new DynamicPlugin instance.
        """
        pm = plugin_manager or self.plugin_manager
        assert isinstance(pm, PluginManager), "plugin_manager must be a PluginManager"

        if name:
            assert name not in pm._manifests, f"name {name!r} already in plugin manager"
            _name = name
        else:
            i = 1
            while (_name := f"{self.name}-{i}") in pm._manifests:
                i += 1

        new = type(self)(_name, plugin_manager=pm)
        if register:
            new.register()
        return new


class ContributionDecorators:
    """A set of decorators that facilitate adding contributions to a TemporaryPlugin.

    Examples
    --------
    >>> with TemporaryPlugin('name') as p:
    >>>     @p.contribute.sample_data
    >>>     def make_data() -> np.ndarray: ...
    >>>
    """

    def __init__(self, plugin: DynamicPlugin) -> None:
        self.plugin = plugin
        self.command = ContributionDecorator(plugin, CommandContribution)
        self.reader = ContributionDecorator(plugin, ReaderContribution)
        self.writer = ContributionDecorator(plugin, WriterContribution)
        self.widget = ContributionDecorator(plugin, WidgetContribution)
        self.sample_data = ContributionDecorator(plugin, SampleDataGenerator)


class ContributionDecorator(Generic[C]):
    """An actual instance of a contribution decorator.

    This holds the logic for actually adding a decorated function as a contribution
    of a specific `contrib_type` to a temporary plugin.
    """

    def __init__(self, plugin: DynamicPlugin, contrib_type: Type[C]) -> None:
        self.plugin = plugin
        self.contrib_type = contrib_type
        self._contrib_name = CONTRIB_NAMES[self.contrib_type]

    @overload
    def __call__(self, func: T, **kwargs) -> T:
        ...

    @overload
    def __call__(
        self, func: Optional[Literal[None]] = None, **kwargs
    ) -> Callable[[T], T]:
        ...

    def __call__(
        self, func: Optional[T] = None, **kwargs
    ) -> Union[T, Callable[[T], T]]:
        """Decorate function as providing this contrubtion type.

        This is the actual decorator used when one calls, eg.
        >>> @npe2plugin.contribute.reader
        >>> def some_func(path):
        >>>     ...
        """

        def _mark_contribution(_func: T, _kwargs=kwargs) -> T:
            try:
                self._set_defaults(_func, _kwargs)
                _kwargs = self._store_command(_func, _kwargs)
                self._store_contrib(_kwargs)
                self.plugin.plugin_manager._contrib.reindex(self._mf)
            except ValidationError as e:
                # cleanup any added commands
                if "command" in _kwargs:
                    new = [c for c in self.commands if c.id != _kwargs["command"]]
                    self._mf.contributions.commands = new
                    self.plugin.plugin_manager.commands.unregister(_kwargs["command"])
                raise AssertionError(
                    f"Invalid decorator for {self.contrib_type.__name__}.\n{e}"
                ) from e

            return _func

        return _mark_contribution if func is None else _mark_contribution(func)

    def _set_defaults(self, _func: T, kwargs: dict) -> None:
        """Populate contribution kwargs with reasonable type-specific defaults"""
        if self.contrib_type is ReaderContribution:
            kwargs.setdefault("filename_patterns", ["*"])
        if self.contrib_type is SampleDataGenerator:
            kwargs.setdefault("key", _func.__name__)
            kwargs.setdefault("display_name", _func.__name__)
        if self.contrib_type is WriterContribution:
            kwargs.setdefault("layer_types", [])

    def _store_contrib(self, kwargs: dict) -> None:
        """Store the new contribution in the manifest"""
        if self.contrib_type is not CommandContribution:
            self.contribution_list.append(self.contrib_type(**kwargs))

    def _store_command(self, func: T, kwargs: dict) -> dict:
        """Create a new command contribution for `func`"""
        kwargs.setdefault("title", func.__name__)
        kwargs.setdefault("id", f"{self.plugin.manifest.name}.{func.__name__}")
        cmd_kwargs = {
            k: kwargs.pop(k)
            for k in list(kwargs)
            if k in CommandContribution.__fields__
        }
        cmd = CommandContribution(**cmd_kwargs)
        self.commands.append(cmd)
        self.plugin.plugin_manager.commands.register(cmd.id, func)
        kwargs["command"] = cmd.id
        return kwargs

    @property
    def _mf(self) -> PluginManifest:
        """Return all contributions in currently in the temporary plugin"""
        return self.plugin.manifest

    @property
    def contribution_list(self) -> List[C]:
        """Return contributions of this type in the associated manifest."""
        if not getattr(self._mf.contributions, self._contrib_name):
            setattr(self._mf.contributions, self._contrib_name, [])
        return getattr(self._mf.contributions, self._contrib_name)

    @property
    def commands(self) -> List[CommandContribution]:
        """Return the CommandContributions in the associated manifest."""
        if not self._mf.contributions.commands:
            self._mf.contributions.commands = []
        return self._mf.contributions.commands
