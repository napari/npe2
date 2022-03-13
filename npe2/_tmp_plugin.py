from __future__ import annotations

import inspect
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from pydantic import BaseModel, ValidationError
from typing_extensions import Literal

from npe2.manifest.contributions import ContributionPoints

from ._plugin_manager import PluginManager
from .manifest.commands import CommandContribution
from .manifest.readers import ReaderContribution
from .manifest.sample_data import SampleDataGenerator, SampleDataURI
from .manifest.schema import PluginManifest
from .manifest.widgets import WidgetContribution
from .manifest.writers import WriterContribution

C = TypeVar("C", bound=BaseModel)
T = TypeVar("T", bound=Callable[..., Any])

COMMAND_PARAMS = inspect.signature(CommandContribution).parameters
# TODO: pull this map from ContributionPoints
CONTRIB_NAMES: Dict[Type[BaseModel], str] = {
    CommandContribution: "commands",
    ReaderContribution: "readers",
    WriterContribution: "writers",
    WidgetContribution: "widgets",
    SampleDataGenerator: "sample_data",
    SampleDataURI: "sample_data",
}


class ContribDecoInstance(Generic[C]):
    """An actual instance of a contribution decorator.

    This holds the logic for actually adding a decorated function as a contribution
    of a specific `contrib_type` to a temporary plugin.
    """

    def __init__(self, plugin: TemporaryPlugin, contrib_type: Type[C]) -> None:
        self.plugin = plugin
        self.contrib_type = contrib_type
        self._contrib_name = CONTRIB_NAMES[self.contrib_type]

    # This is the actual decorator used when one calls, eg.
    # @npe2plugin.contribute.reader

    @overload
    def __call__(self, func: T, **kwargs) -> T:
        ...

    @overload
    def __call__(self, func: Literal[None] = None, **kwargs) -> Callable[[T], T]:
        ...

    def __call__(
        self, func: Optional[T] = None, **kwargs
    ) -> Union[T, Callable[[T], T]]:
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

    def _set_defaults(self, _func: T, kwargs: dict):
        """populate contribution kwargs with reasonable type-specific defaults"""
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
        cmd_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in COMMAND_PARAMS}
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
        if not getattr(self._mf.contributions, self._contrib_name):
            setattr(self._mf.contributions, self._contrib_name, [])
        return getattr(self._mf.contributions, self._contrib_name)

    @property
    def commands(self) -> List[CommandContribution]:
        if not self._mf.contributions.commands:
            self._mf.contributions.commands = []
        return self._mf.contributions.commands


class ContributionDecorator(Generic[C]):
    """Contribution decorator bound to a specific contribution type."""

    def __init__(self, contrib_type: Type[C]) -> None:
        self.contrib_type = contrib_type
        self._name: Optional[str] = None

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        if self._name is None:
            self._name = name

    @overload
    def __get__(
        self, decos: None, owner: Optional[Type[ContributionDecorators]] = None
    ) -> ContributionDecorator:
        ...

    @overload
    def __get__(
        self,
        decos: ContributionDecorators,
        owner: Optional[Type[ContributionDecorators]] = None,
    ) -> ContribDecoInstance:
        ...

    def __get__(
        self,
        decos: Optional[ContributionDecorators],
        owner: Optional[Type[ContributionDecorators]] = None,
    ) -> Union[ContributionDecorator, ContribDecoInstance]:
        if decos is None:  # pragma: no cover
            return self
        inst = ContribDecoInstance(decos.plugin, self.contrib_type)
        setattr(decos, cast(str, self._name), inst)
        return inst


class ContributionDecorators:
    """A set of decorators that facilitate adding contributions to a TemporaryPlugin.

    Examples
    --------
    >>> with TemporaryPlugin('name') as p:
    >>>     @p.contribute.sample_data
    >>>     def make_data() -> np.ndarray: ...
    >>>
    """

    command = ContributionDecorator(CommandContribution)
    reader = ContributionDecorator(ReaderContribution)
    writer = ContributionDecorator(WriterContribution)
    widget = ContributionDecorator(WidgetContribution)
    sample_data = ContributionDecorator(SampleDataGenerator)

    def __init__(self, plugin: TemporaryPlugin) -> None:
        self.plugin = plugin


class TemporaryPlugin:
    def __init__(
        self,
        name: str = "temp-plugin",
        plugin_manager: Optional[PluginManager] = None,
    ) -> None:
        self.manifest = PluginManifest(name=name)
        self.contribute = ContributionDecorators(self)
        self._pm = plugin_manager

    def cleanup(self):
        """Remove this plugin from its plugin manager"""
        self.plugin_manager.unregister(self.manifest.name)

    def register(self):
        """Remove this plugin from its plugin manager"""
        self.plugin_manager.register(self.manifest)

    def clear(self):
        """Clear contributions."""
        self.plugin_manager._contrib.remove_contributions(self.manifest.name)
        self.manifest.contributions = ContributionPoints()

    @property
    def plugin_manager(self) -> PluginManager:
        """Return the plugin manager this plugin is registered in.

        If unset, will use the global plugin manager instance.
        """
        return self._pm or PluginManager.instance()

    @plugin_manager.setter
    def plugin_manager(self, pm: Optional[PluginManager]):
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

    def __enter__(self):
        self.register()
        return self

    def __exit__(self, *_):
        self.cleanup()
