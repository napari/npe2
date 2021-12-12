import itertools
import re
import sys
import warnings
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from napari_plugin_engine import (
    HookCaller,
    HookImplementation,
    PluginManager,
    napari_hook_specification,
)

from npe2.manifest import PluginManifest
from npe2.manifest.commands import CommandContribution
from npe2.manifest.schema import ENGINE_VERSION
from npe2.manifest.themes import ThemeColors
from npe2.manifest.widgets import WidgetContribution

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


# fmt: off
class HookSpecs:
    def napari_provide_sample_data(): ...  # type: ignore  # noqa: E704
    def napari_get_reader(path): ...  # noqa: E704
    def napari_get_writer(path, layer_types): ...  # noqa: E704
    def napari_write_image(path, data, meta): ...  # noqa: E704
    def napari_write_labels(path, data, meta): ...  # noqa: E704
    def napari_write_points(path, data, meta): ...  # noqa: E704
    def napari_write_shapes(path, data, meta): ...  # noqa: E704
    def napari_write_surface(path, data, meta): ...  # noqa: E704
    def napari_write_vectors(path, data, meta): ...  # noqa: E704
    def napari_experimental_provide_function(): ...  # type: ignore  # noqa: E704
    def napari_experimental_provide_dock_widget(): ...  # type: ignore  # noqa: E704
    def napari_experimental_provide_theme(): ...  # type: ignore  # noqa: E704
# fmt: on


for m in dir(HookSpecs):
    if m.startswith("napari"):
        setattr(HookSpecs, m, napari_hook_specification(getattr(HookSpecs, m)))


WidgetCallable = Union[Callable, Tuple[Callable, dict]]


@dataclass
class PluginPackage:
    package_name: str
    ep_name: str
    ep_value: str
    top_module: str

    @property
    def name_pairs(self):
        names = (self.ep_name, self.package_name, self.top_module)
        return itertools.product(names, repeat=2)


@lru_cache()
def plugin_packages() -> List[PluginPackage]:
    """List of all packages with napari entry points.

    This is useful to help resolve naming issues (due to the terrible confusion
    around *what* a npe1 plugin name actually was).
    """

    packages = []
    for dist in metadata.distributions():
        for ep in dist.entry_points:
            if ep.group != "napari.plugin":
                continue
            top = dist.read_text("top_level.txt")
            top = top.splitlines()[0] if top else ep.value.split(".")[0]
            packages.append(
                PluginPackage(dist.metadata["Name"], ep.name, ep.value, top)
            )
    return packages


@lru_cache()
def npe1_plugin_manager() -> Tuple[PluginManager, Tuple[int, list]]:
    pm = PluginManager("napari", discover_entry_point="napari.plugin")
    pm.add_hookspecs(HookSpecs)
    result = pm.discover()
    return pm, result


def norm_plugin_name(plugin_name: Optional[str] = None, module: Any = None) -> str:
    """Try all the things we know to detect something called `plugin_name`."""
    plugin_manager, (_, errors) = npe1_plugin_manager()

    # directly providing a module is mostly for testing.
    if module is not None:
        if plugin_name:  # pragma: no cover
            warnings.warn("module provided, plugin_name ignored")
        plugin_name = getattr(module, "__name__", "dynamic_plugin")
        if not plugin_manager.is_registered(plugin_name):
            plugin_manager.register(module, plugin_name)
        return cast(str, plugin_name)

    if plugin_name in plugin_manager.plugins:
        return cast(str, plugin_name)

    for pkg in plugin_packages():
        for a, b in pkg.name_pairs:
            if plugin_name == a and b in plugin_manager.plugins:
                return b

    # we couldn't find it:
    for e in errors:
        if module and e.plugin == module:
            raise type(e)(e.format())
        for pkg in plugin_packages():
            if plugin_name in (pkg.ep_name, pkg.package_name, pkg.top_module):
                raise type(e)(e.format())

    msg = f"We tried hard! but could not detect a plugin named {plugin_name!r}."
    if plugin_manager.plugins:
        msg += f" Plugins found include: {list(plugin_manager.plugins)}"
    raise PackageNotFoundError(msg)


def manifest_from_npe1(
    plugin_name: Optional[str] = None, module: Any = None
) -> PluginManifest:
    plugin_manager, _ = npe1_plugin_manager()
    plugin_name = norm_plugin_name(plugin_name, module)

    _module = plugin_manager.plugins[plugin_name]
    standard_meta = plugin_manager.get_standard_metadata(plugin_name)
    package = standard_meta.get("package")
    if not package:
        if module is not None:
            package = "dynamic"
        else:
            # NOTE: this is more of an assertion error, shouldn't happen.
            raise ModuleNotFoundError(
                f"Could not find package for plugin {plugin_name!r}"
            )

    parser = HookImplParser(package, plugin_name)
    parser.parse_callers(plugin_manager._plugin2hookcallers[_module])

    return PluginManifest(
        name=package,
        engine=ENGINE_VERSION,
        contributions=dict(parser.contributions),
    )


class HookImplParser:
    def __init__(self, package: str, plugin_name: str) -> None:
        self.package = package
        self.plugin_name = plugin_name
        self.contributions: DefaultDict[str, list] = DefaultDict(list)

    def parse_callers(self, callers: Iterable[HookCaller]):
        for caller in callers:
            for impl in caller.get_hookimpls():
                if self.plugin_name and impl.plugin_name != self.plugin_name:
                    continue
                # call the corresponding hookimpl parser
                try:
                    getattr(self, impl.specname)(impl)
                except Exception as e:  # pragma: no cover
                    warnings.warn(f"Failed to convert {impl.specname}: {e}")

    def napari_experimental_provide_theme(self, impl: HookImplementation):
        ThemeDict = Dict[str, Union[str, Tuple, List]]
        d: Dict[str, ThemeDict] = impl.function()
        for name, theme_dict in d.items():
            colors = ThemeColors(**theme_dict)
            clr = colors.background or colors.foreground
            luma = _luma(*clr.as_rgb_tuple()[:3]) if clr else 0
            self.contributions["themes"].append(
                {
                    "label": name,
                    "id": name.lower().replace(" ", "_"),
                    "type": "dark" if luma < 128 else "light",
                    "colors": colors,
                }
            )

    def napari_get_reader(self, impl: HookImplementation):
        self.contributions["readers"].append(
            {
                "command": self.add_command(impl),
                "accepts_directories": True,
                "filename_patterns": ["<EDIT_ME>"],
            }
        )

    def napari_provide_sample_data(self, impl: HookImplementation):
        module = sys.modules[impl.function.__module__.split(".", 1)[0]]
        package_dir = module.__file__.rsplit("/", 1)[0]

        samples: Dict[str, Union[dict, str, Callable]] = impl.function()
        for key, sample in samples.items():
            _sample: Union[str, Callable]
            if isinstance(sample, dict):
                display_name = sample.get("display_name")
                _sample = sample.get("data")  # type: ignore
            else:
                _sample = sample
                display_name = key

            _key = _safe_key(key)
            s = {"key": _key, "display_name": display_name}
            if callable(_sample):
                # let these raise exceptions here immediately if they don't validate
                id = f"{self.package}.data.{_key}"
                cmd_contrib = CommandContribution(
                    id=id,
                    python_name=_python_name(_sample),
                    title=f"{key} sample",
                )
                self.contributions["commands"].append(cmd_contrib)
                s["command"] = id
            else:
                s["uri"] = str(_sample).replace(package_dir, r"${package}")

            self.contributions["sample_data"].append(s)

    def napari_experimental_provide_function(self, impl: HookImplementation):
        items: Union[Callable, List[Callable]] = impl.function()
        if not isinstance(items, list):
            items = [items]
        for idx, item in enumerate(items):
            try:

                cmd = f"{self.package}.{item.__name__}"
                py_name = _python_name(item)

                docsum = item.__doc__.splitlines()[0] if item.__doc__ else None
                cmd_contrib = CommandContribution(
                    id=cmd, python_name=py_name, title=docsum or item.__name__
                )
                self.contributions["commands"].append(cmd_contrib)

                wdg_contrib = WidgetContribution(
                    command=cmd,
                    display_name=item.__name__.replace("_", " "),
                    autogenerate=True,
                )
                self.contributions["widgets"].append(wdg_contrib)

            except Exception as e:
                msg = (
                    f"Error converting function [{idx}] "
                    f"from {impl.function.__module__!r}:\n{e}"
                )
                warnings.warn(msg)

    def napari_experimental_provide_dock_widget(self, impl: HookImplementation):
        items: Union[WidgetCallable, List[WidgetCallable]] = impl.function()
        if not isinstance(items, list):
            items = [items]  # pragma: no cover

        for idx, item in enumerate(items):
            if isinstance(item, tuple):
                wdg_creator = item[0]
                kwargs = item[1] if len(item) > 1 else {}
            else:
                wdg_creator, kwargs = (item, {})
            if not callable(wdg_creator) and isinstance(kwargs, dict):
                warnings.warn(f"Invalid widget spec: {wdg_creator}, {kwargs}")
                continue

            try:
                self._create_widget_contrib(impl, wdg_creator, kwargs)
            except Exception as e:
                msg = (
                    f"Error converting dock widget [{idx}] "
                    f"from {impl.function.__module__!r}:\n{e}"
                )
                warnings.warn(msg)

    def _create_widget_contrib(self, impl, wdg_creator, kwargs, is_function=False):
        # Get widget name
        func_name = getattr(wdg_creator, "__name__", "")
        wdg_name = str(kwargs.get("name", "")) or _camel_to_spaces(func_name)

        # in some cases, like partials and magic_factories, there might not be an
        # easily accessible python name (from __module__.__qualname__)...
        # so first we look for this object in the module namespace
        py_name = None
        cmd = None
        for local_name, val in impl.function.__globals__.items():
            if val is wdg_creator:
                py_name = f"{impl.function.__module__}:{local_name}"
                cmd = f"{self.package}.{local_name}"
                break
        else:
            try:
                py_name = _python_name(wdg_creator)
                cmd = (
                    f"{self.package}.{func_name or wdg_name.lower().replace(' ', '_')}"
                )
            except AttributeError:
                pass

        if not py_name:
            raise ValueError(
                "No suitable python name to point to. "
                "Is this a locally defined function or partial?"
            )

        # let these raise exceptions here immediately if they don't validate
        cmd_contrib = CommandContribution(
            id=cmd, python_name=py_name, title=f"Create {wdg_name}"
        )
        wdg_contrib = WidgetContribution(command=cmd, display_name=wdg_name)
        self.contributions["commands"].append(cmd_contrib)
        self.contributions["widgets"].append(wdg_contrib)

    def napari_get_writer(self, impl: HookImplementation):
        warnings.warn(
            "Found a multi-layer writer, but it's not convertable. "
            "Please add the writer manually."
        )
        return NotImplemented

    def napari_write_image(self, impl: HookImplementation):
        self._parse_writer(impl, "image")

    def napari_write_labels(self, impl: HookImplementation):
        self._parse_writer(impl, "labels")

    def napari_write_points(self, impl: HookImplementation):
        self._parse_writer(impl, "points")

    def napari_write_shapes(self, impl: HookImplementation):
        self._parse_writer(impl, "shapes")

    def napari_write_vectors(self, impl: HookImplementation):
        self._parse_writer(impl, "vectors")

    def _parse_writer(self, impl: HookImplementation, layer: str):
        id = self.add_command(impl)
        self.contributions["writers"].append(
            {
                "command": id,
                "layer_types": [layer],
                "display_name": layer,
                "filename_extensions": ["<EDIT_ME>"],
            }
        )

    def add_command(self, impl: HookImplementation, py_name: str = "") -> str:
        name = impl.specname.replace("napari_", "")
        id = f"{self.package}.{name}"
        title = " ".join(name.split("_")).title()
        if not py_name:
            py_name = _python_name(impl.function)
        c = CommandContribution(id=id, python_name=py_name, title=title)
        self.contributions["commands"].append(c)
        return id


def _safe_key(key: str) -> str:
    return (
        key.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("[", "")
        .replace("]", "")
    )


def _python_name(object):
    return f"{object.__module__}:{object.__qualname__}"


def _luma(r, g, b):
    # https://en.wikipedia.org/wiki/Luma_(video)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b  # per ITU-R BT.709


_camel_to_spaces_pattern = re.compile(r"((?<=[a-z])[A-Z]|(?<!\A)[A-R,T-Z](?=[a-z]))")


def _camel_to_spaces(val):
    return _camel_to_spaces_pattern.sub(r" \1", val)
