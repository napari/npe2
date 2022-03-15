import ast
import itertools
import re
import sys
import warnings
from configparser import ConfigParser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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
from npe2.manifest.themes import ThemeColors
from npe2.manifest.widgets import WidgetContribution

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore

NPE1_EP = "napari.plugin"
NPE2_EP = "napari.manifest"


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


@dataclass
class PluginPackage:
    package_name: str
    ep_name: str
    ep_value: str
    top_module: str
    setup_cfg: Optional[Path] = None

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
            if ep.group != NPE1_EP:
                continue  # pragma: no cover
            top = dist.read_text("top_level.txt")
            top = top.splitlines()[0] if top else ep.value.split(".")[0]
            packages.append(
                PluginPackage(dist.metadata["Name"], ep.name, ep.value, top)
            )
    return packages


def ensure_package_name(name: str):
    """Try all the tricks we know to find a package name given a plugin name."""
    for attr in ("package_name", "ep_name", "top_module"):
        for p in plugin_packages():
            if name == getattr(p, attr):
                return p.package_name
    raise KeyError(  # pragma: no cover
        f"Unable to find a locally installed package for plugin {name!r}"
    )


@lru_cache()
def npe1_plugin_manager() -> Tuple[PluginManager, Tuple[int, list]]:
    pm = PluginManager("napari", discover_entry_point=NPE1_EP)
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
    for e in errors:  # pragma: no cover
        if module and e.plugin == module:
            raise type(e)(e.format())
        for pkg in plugin_packages():
            if plugin_name in (pkg.ep_name, pkg.package_name, pkg.top_module):
                raise type(e)(e.format())

    msg = f"We tried hard! but could not detect a plugin named {plugin_name!r}."
    if plugin_manager.plugins:
        msg += f" Plugins found include: {list(plugin_manager.plugins)}"
    raise metadata.PackageNotFoundError(msg)


def manifest_from_npe1(
    plugin_name: Optional[str] = None, module: Any = None
) -> PluginManifest:
    """Return manifest object given npe1 plugin_name or package name.

    One of `plugin_name` or `module` must be provide.

    Parameters
    ----------
    plugin_name : str
        Name of package/plugin to convert, by default None
    module : Module
        namespace object, to directly import (mostly for testing.), by default None
    """
    plugin_manager, _ = npe1_plugin_manager()
    plugin_name = norm_plugin_name(plugin_name, module)

    _module = plugin_manager.plugins[plugin_name]
    package = ensure_package_name(plugin_name) if module is None else "dynamic"

    parser = HookImplParser(package, plugin_name)
    parser.parse_callers(plugin_manager._plugin2hookcallers[_module])

    return PluginManifest(name=package, contributions=dict(parser.contributions))


class HookImplParser:
    def __init__(self, package: str, plugin_name: str) -> None:
        self.package = package
        self.plugin_name = plugin_name
        self.contributions: DefaultDict[str, list] = DefaultDict(list)

    def parse_callers(self, callers: Iterable[HookCaller]):
        for caller in callers:
            for impl in caller.get_hookimpls():
                if self.plugin_name and impl.plugin_name != self.plugin_name:
                    continue  # pragma: no cover
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
                assert module.__file__
                package_dir = module.__file__.rsplit("/", 1)[0]
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

            except Exception as e:  # pragma: no cover
                msg = (
                    f"Error converting function [{idx}] "
                    f"from {impl.function.__module__!r}:\n{e}"
                )
                warnings.warn(msg)

    def napari_experimental_provide_dock_widget(self, impl: HookImplementation):
        WidgetCallable = Union[Callable, Tuple[Callable, dict]]
        items: Union[WidgetCallable, List[WidgetCallable]] = impl.function()
        if not isinstance(items, list):
            items = [items]  # pragma: no cover

        for idx, item in enumerate(items):
            if isinstance(item, tuple):
                wdg_creator = item[0]
                kwargs = item[1] if len(item) > 1 else {}
            else:
                wdg_creator, kwargs = (item, {})
            if not callable(wdg_creator) and isinstance(
                kwargs, dict
            ):  # pragma: no cover
                warnings.warn(f"Invalid widget spec: {wdg_creator}, {kwargs}")
                continue

            try:
                self._create_widget_contrib(impl, wdg_creator, kwargs)
            except Exception as e:  # pragma: no cover
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
            except AttributeError:  # pragma: no cover
                pass

        if not py_name:  # pragma: no cover
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
        return NotImplemented  # pragma: no cover

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


def get_top_module_path(package_name, top_module: Optional[str] = None) -> Path:
    dist = metadata.distribution(package_name)
    if not top_module:
        top_mods = (dist.read_text("top_level.txt") or "").strip().splitlines()
        if not top_mods:
            raise ValueError(  # pragma: no cover
                "Could not detect a top level module in distribution metadata "
                f"for {package_name}"
            )
        top_module = top_mods[0]

    path = Path(dist.locate_file(top_module))
    assert path.is_dir()
    return path


def convert_repository(
    path: Union[Path, str], mf_name: str = "napari.yaml", dry_run=False
) -> Tuple[PluginManifest, Path]:
    """Convert repository at `path` to new npe2 style."""
    path = Path(path)

    # get the info we need and create a manifest
    info = get_package_dir_info(path)
    manifest = manifest_from_npe1(info.package_name)
    top_module = get_top_module_path(info.package_name, info.top_module)
    if not top_module.is_dir():
        raise ValueError(  # pragma: no cover
            f"Detection of top-level module failed. {top_module} is not a directory."
        )
    mf_path = top_module / mf_name

    if dry_run:
        return manifest, mf_path

    # update the entry_points in setup.cfg/setup.py
    if info.setup_cfg:
        _write_new_setup_cfg_ep(info, mf_name)
    # or tell them to do it themselves in setup.py
    else:
        # tell them to do it manually
        warnings.warn(
            "\nCannot auto-update setup.py, please edit setup.py as follows:\n"
            "  1. remove the `napari.plugin` entry_point\n"
            "  2. add the following entry_point:"
            f"""
       entry_points={{
           "{NPE2_EP}": [
               "{info.package_name} = {info.top_module}:{mf_name}",
           ],
       }},
       package_data={{"{info.top_module}": ["{mf_name}"]}},
"""
        )

    # write the yaml to top_module/napari.yaml
    mf_path.write_text(manifest.yaml())
    return manifest, mf_path


def _write_new_setup_cfg_ep(info: PluginPackage, mf_name: str):
    assert info.setup_cfg
    p = ConfigParser(comment_prefixes="/", allow_no_value=True)  # preserve comments
    p.read(info.setup_cfg)
    mf_path = f"{info.top_module}:{mf_name}"
    new_ep = f"\n{info.package_name} = {mf_path}"
    if "options.entry_points" not in p.sections():
        p.add_section("options.entry_points")  # pragma: no cover
    p.set("options.entry_points", NPE2_EP, new_ep)
    if "options.package_data" not in p.sections():
        p.add_section("options.package_data")
    p.set("options.package_data", info.top_module, mf_name)
    if "options" not in p.sections():
        p.add_section("options")
    p.set("options", "include_package_data", "True")
    p.remove_option("options.entry_points", NPE1_EP)
    with open(info.setup_cfg, "w") as fh:
        p.write(fh)


def get_package_dir_info(path: Union[Path, str]) -> PluginPackage:
    """Attempts to *statically* get plugin info from a package directory."""
    path = Path(path).absolute()
    if not path.is_dir():  # pragma: no cover
        raise ValueError(f"Provided path is not a directory: {path}")

    _name = None
    _entry_points: List[List[str]] = []
    _setup_cfg = None
    p = None

    # check for setup.cfg
    setup_cfg = path / "setup.cfg"
    if setup_cfg.exists():
        _setup_cfg = setup_cfg
        p = ConfigParser()
        p.read(setup_cfg)
        _name = p.get("metadata", "name", fallback=None)
        eps = p.get("options.entry_points", NPE1_EP, fallback="").strip()
        _entry_points = [[i.strip() for i in ep.split("=")] for ep in eps.splitlines()]

    if not _name or not _entry_points:
        # check for setup.py
        setup_py = path / "setup.py"
        if setup_py.exists():
            node = ast.parse(setup_py.read_text())
            visitor = _SetupVisitor()
            visitor.visit(node)
            _name = _name or visitor._name
            if visitor._entry_points and not _entry_points:
                _entry_points = visitor._entry_points
                _setup_cfg = None  # the ep metadata wasn't in setupcfg

    if _name and _entry_points:
        ep_name, ep_value = next(iter(_entry_points), ["", ""])
        top_mod = ep_value.split(".", 1)[0]
        return PluginPackage(_name, ep_name, ep_value, top_mod, _setup_cfg)

    msg = f'Could not detect first gen napari plugin package at "{path}".'
    if p is not None and p.get("options.entry_points", NPE2_EP, fallback=False):
        msg += f" Found a {NPE2_EP} entry_point. Is this package already converted?"
    raise ValueError(msg)


class _SetupVisitor(ast.NodeVisitor):
    """Visitor to statically determine metadata from setup.py"""

    def __init__(self) -> None:
        super().__init__()
        self._name: str = ""
        self._entry_points: List[List[str]] = []  # [[name, value], ...]

    def visit_Call(self, node: ast.Call) -> Any:
        if getattr(node.func, "id", "") != "setup":
            return  # pragma: no cover
        for kw in node.keywords:
            if kw.arg == "name":
                self._name = (
                    getattr(kw.value, "value", "")
                    or getattr(kw.value, "id", "")
                    or getattr(kw.value, "s", "")  # py3.7
                )

            if kw.arg == "entry_points":
                eps: dict = ast.literal_eval(kw.value)
                for k, v in eps.items():
                    if k == NPE1_EP:
                        if type(v) is str:
                            v = [v]
                        for item in v:
                            self._entry_points.append(
                                [i.strip() for i in item.split("=")]
                            )
