import ast
import inspect
import re
import sys
import warnings
from configparser import ConfigParser
from functools import lru_cache, partial
from importlib import import_module, metadata
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from npe2.manifest import PluginManifest
from npe2.manifest.contributions import (
    CommandContribution,
    ThemeColors,
    WidgetContribution,
)
from npe2.manifest.utils import (
    SHIM_NAME_PREFIX,
    import_python_name,
    merge_manifests,
    safe_key,
)
from npe2.types import WidgetCreator

from ._setuputils import PackageInfo, get_package_dir_info

logger = getLogger(__name__)
NPE1_EP = "napari.plugin"
NPE2_EP = "napari.manifest"
NPE1_IMPL_TAG = "napari_impl"  # same as HookImplementation.format_tag("napari")


class HookImplementation:
    def __init__(
        self,
        function: Callable,
        plugin: Optional[ModuleType] = None,
        plugin_name: Optional[str] = None,
        **kwargs,
    ):
        self.function = function
        self.plugin = plugin
        self.plugin_name = plugin_name
        self._specname = kwargs.get("specname")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HookImplementation plugin={self.plugin_name!r} spec={self.specname!r}>"
        )

    @property
    def specname(self) -> str:
        return self._specname or self.function.__name__


def iter_hookimpls(
    module: ModuleType, plugin_name: Optional[str] = None
) -> Iterator[HookImplementation]:
    # yield all routines in module that have "{self.project_name}_impl" attr
    for name in dir(module):
        method = getattr(module, name)
        if hasattr(method, NPE1_IMPL_TAG) and inspect.isroutine(method):
            hookimpl_opts = getattr(method, NPE1_IMPL_TAG)
            if isinstance(hookimpl_opts, dict):
                yield HookImplementation(method, module, plugin_name, **hookimpl_opts)


@lru_cache
def plugin_packages() -> List[PackageInfo]:
    """List of all packages with napari entry points.

    This is useful to help resolve naming issues (due to the terrible confusion
    around *what* a npe1 plugin name actually was).
    """

    packages: List[PackageInfo] = []
    for dist in metadata.distributions():
        packages.extend(
            PackageInfo(package_name=dist.metadata["Name"], entry_points=[ep])
            for ep in dist.entry_points
            if ep.group == NPE1_EP
        )

    return packages


def manifest_from_npe1(
    plugin: Union[str, metadata.Distribution, None] = None,
    module: Optional[Any] = None,
    adapter=False,
) -> PluginManifest:
    """Return manifest object given npe1 plugin or package name.

    One of `plugin` or `module` must be provide.

    Parameters
    ----------
    plugin : Union[str, metadata.Distribution, None]
        Name of package/plugin to convert.  Or a `metadata.Distribution` object.
        If a string, this function should be prepared to accept both the name of the
        package, and the name of an npe1 `napari.plugin` entry_point. by default None
    module : Optional[Module]
        namespace object, to directly import (mostly for testing.), by default None
    adapter : bool
        If True, the resulting manifest will be used internally by NPE1Adapter, but
        is NOT necessarily suitable for export as npe2 manifest. This will handle
        cases of locally defined functions and partials that don't have global
        python_names that are not supported natively by npe2. by default False
    """
    if module is not None:
        modules: List[str] = [module]
        package_name = "dynamic"
        plugin_name = getattr(module, "__name__", "dynamic_plugin")
    elif isinstance(plugin, str):
        modules = []
        plugin_name = plugin
        for pp in plugin_packages():
            if plugin in (pp.ep_name, pp.package_name):
                modules.append(pp.ep_value)
                package_name = pp.package_name
        if not modules:
            _avail = [f"  {p.package_name} ({p.ep_name})" for p in plugin_packages()]
            avail = "\n".join(_avail)
            raise metadata.PackageNotFoundError(
                f"No package or entry point found with name {plugin!r}: "
                f"\nFound packages (entry_point):\n{avail}"
            )
    elif hasattr(plugin, "entry_points") and hasattr(plugin, "metadata"):
        plugin = cast(metadata.Distribution, plugin)
        # don't use isinstance(Distribution), setuptools monkeypatches sys.meta_path:
        # https://github.com/pypa/setuptools/issues/3169
        NPE1_ENTRY_POINT = "napari.plugin"
        plugin_name = package_name = plugin.metadata["Name"]
        modules = [
            ep.value for ep in plugin.entry_points if ep.group == NPE1_ENTRY_POINT
        ]
        assert modules, f"No npe1 entry points found in distribution {plugin_name!r}"
    else:
        raise ValueError("one of plugin or module must be provided")  # pragma: no cover

    manifests: List[PluginManifest] = []
    for mod_name in modules:
        logger.debug(
            "Discovering contributions for npe1 plugin %r: module %r",
            package_name,
            mod_name,
        )
        parser = HookImplParser(package_name, plugin_name or "", adapter=adapter)
        _mod = import_module(mod_name) if isinstance(mod_name, str) else mod_name
        parser.parse_module(_mod)
        manifests.append(parser.manifest())

    assert manifests, "No npe1 entry points found in distribution {name}"
    return merge_manifests(manifests)


class HookImplParser:
    def __init__(self, package: str, plugin_name: str, adapter: bool = False) -> None:
        """A visitor class to convert npe1 hookimpls to a npe2 manifest

        Parameters
        ----------
        package : str
            Name of package
        plugin_name : str
            Name of plugin (will almost always be name of package)
        adapter : bool, optional
            If True, the resulting manifest will be used internally by NPE1Adapter, but
            is NOT necessarily suitable for export as npe2 manifest. This will handle
            cases of locally defined functions and partials that don't have global
            python_names that are not supported natively by npe2. by default False

        Examples
        --------
        >>> parser = HookImplParser(package, plugin_name)
        >>> parser.parse_callers(plugin_manager._plugin2hookcallers[_module])
        >>> mf = PluginManifest(name=package, contributions=dict(parser.contributions))
        """
        self.package = package
        self.plugin_name = plugin_name
        self.contributions: DefaultDict[str, list] = DefaultDict(list)
        self.adapter = adapter

    def manifest(self) -> PluginManifest:
        return PluginManifest(name=self.package, contributions=dict(self.contributions))

    def parse_module(self, module: ModuleType):
        for impl in iter_hookimpls(module, plugin_name=self.plugin_name):
            if impl.plugin_name == self.plugin_name:
                # call the corresponding hookimpl parser
                try:
                    getattr(self, impl.specname)(impl)
                except Exception as e:  # pragma: no cover
                    warnings.warn(
                        f"Failed to convert {impl.specname} in {self.package!r}: {e}",
                        stacklevel=2,
                    )

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
        patterns = _guess_fname_patterns(impl.function)

        self.contributions["readers"].append(
            {
                "command": self.add_command(impl),
                "accepts_directories": True,
                "filename_patterns": patterns,
            }
        )

    def napari_provide_sample_data(self, impl: HookImplementation):
        module = sys.modules[impl.function.__module__.split(".", 1)[0]]

        samples: Dict[str, Union[dict, str, Callable]] = impl.function()
        for idx, (key, sample) in enumerate(samples.items()):
            _sample: Union[str, Callable]
            if isinstance(sample, dict):
                display_name = sample.get("display_name")
                _sample = sample.get("data")  # type: ignore
            else:
                _sample = sample
                display_name = key

            _key = safe_key(key)
            s = {"key": _key, "display_name": display_name}
            if callable(_sample):
                # let these raise exceptions here immediately if they don't validate
                id = f"{self.package}.data.{_key}"
                py_name = _python_name(
                    _sample, impl.function, hook_idx=idx if self.adapter else None
                )
                cmd_contrib = CommandContribution(
                    id=id,
                    python_name=py_name,
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
        items = [items] if not isinstance(items, list) else items

        for idx, item in enumerate(items):
            try:
                cmd = f"{self.package}.{item.__name__}"
                py_name = _python_name(
                    item, impl.function, hook_idx=idx if self.adapter else None
                )
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
                warnings.warn(msg, stacklevel=2)

    def napari_experimental_provide_dock_widget(self, impl: HookImplementation):
        WidgetCallable = Union[Callable, Tuple[Callable, dict]]
        items: Union[WidgetCallable, List[WidgetCallable]] = impl.function()
        if not isinstance(items, list):
            items = [items]  # pragma: no cover

        # "wdg_creator" will be the function given by the plugin that returns a widget
        # while `impl` is the hook implementation that returned all the `wdg_creators`
        for idx, item in enumerate(items):
            if isinstance(item, tuple):
                wdg_creator = item[0]
                kwargs = item[1] if len(item) > 1 else {}
            else:
                wdg_creator, kwargs = (item, {})
            if not callable(wdg_creator) and isinstance(
                kwargs, dict
            ):  # pragma: no cover
                warnings.warn(
                    f"Invalid widget spec: {wdg_creator}, {kwargs}", stacklevel=2
                )
                continue

            try:
                func_name = getattr(wdg_creator, "__name__", "")
                wdg_name = str(kwargs.get("name", "")) or _camel_to_spaces(func_name)
                self._create_widget_contrib(
                    wdg_creator, display_name=wdg_name, idx=idx, hook=impl.function
                )
            except Exception as e:  # pragma: no cover
                msg = (
                    f"Error converting dock widget [{idx}] "
                    f"from {impl.function.__module__!r}:\n{e}"
                )
                warnings.warn(msg, stacklevel=2)

    def _create_widget_contrib(
        self,
        wdg_creator: WidgetCreator,
        display_name: str,
        idx: int,
        hook: Callable,
    ):
        # we provide both the wdg_creator object itself, as well as the hook impl that
        # returned it... In the case that we can't get an absolute python name to the
        # wdg_creator itself (e.g. it's defined in a local scope), then the py_name
        # will use the hookimpl itself, and the index of the object returned.
        py_name = _python_name(
            wdg_creator, hook, hook_idx=idx if self.adapter else None
        )

        if not py_name:  # pragma: no cover
            raise ValueError(
                "No suitable python name to point to. "
                "Is this a locally defined function or partial?"
            )

        func_name = getattr(wdg_creator, "__name__", "")
        cmd = f"{self.package}.{func_name or display_name.lower().replace(' ', '_')}"

        # let these raise exceptions here immediately if they don't validate
        cmd_contrib = CommandContribution(
            id=cmd, python_name=py_name, title=f"Create {display_name}"
        )
        wdg_contrib = WidgetContribution(command=cmd, display_name=display_name)
        self.contributions["commands"].append(cmd_contrib)
        self.contributions["widgets"].append(wdg_contrib)

    def napari_get_writer(self, impl: HookImplementation):
        warnings.warn(
            f"Found a multi-layer writer in {self.package!r} - {impl.specname!r}, "
            "but it's not convertable. Please add the writer manually.",
            stacklevel=2,
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
                "filename_extensions": [],
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


def _is_magicgui_magic_factory(obj):
    return "magicgui" in sys.modules and isinstance(obj, partial)


def _python_name(
    obj: Any, hook: Optional[Callable] = None, hook_idx: Optional[int] = None
) -> str:
    """Get resolvable python name for `obj` returned from an npe1 `hook` implentation.

    Parameters
    ----------
    obj : Any
        a python obj
    hook : Callable, optional
        the npe1 hook implementation that returned `obj`, by default None.
        This is used both to search the module namespace for `obj`, and also
        in the shim python name if `obj` cannot be found.
    hook_idx : int, optional
        If `obj` cannot be found and `hook_idx` is not None, then a shim name.
        of the form "__npe1shim__.{_python_name(hook)}_{hook_idx}" will be returned.
        by default None.

    Returns
    -------
    str
       a string that can be imported with npe2.manifest.utils.import_python_name

    Raises
    ------
    AttributeError
        If a resolvable string cannot be found
    """
    obj_name: Optional[str] = None
    mod_name: Optional[str] = None
    # first, check the global namespace of the module where the hook was declared
    # if we find `obj` itself, we can just use it.
    if hasattr(hook, "__module__"):
        hook_mod = sys.modules.get(hook.__module__)
        if hook_mod:
            for local_name, _obj in vars(hook_mod).items():
                if _obj is obj:
                    obj_name = local_name
                    mod_name = hook_mod.__name__
                    break

    # trick if it's a magic_factory
    if _is_magicgui_magic_factory(obj):
        f = obj.keywords.get("function")
        if f:
            v = getattr(f, "__globals__", {}).get(getattr(f, "__name__", ""))
            if v is obj:  # pragma: no cover
                mod_name = f.__module__
                obj_name = f.__qualname__

    # if that didn't work get the qualname of the object
    # and, if it's not a locally defined qualname, get the name of the module
    # in which it is defined
    if not (mod_name and obj_name):
        obj_name = getattr(obj, "__qualname__", "")
        if obj_name and "<locals>" not in obj_name:
            mod = inspect.getmodule(obj) or inspect.getmodule(hook)
            if mod:
                mod_name = mod.__name__

    if not (mod_name and obj_name) and (hook and hook_idx is not None):
        # we weren't able to resolve an absolute name... if we are shimming, then we
        # can create a special py_name of the form `__npe1shim__.hookfunction_idx`
        return f"{SHIM_NAME_PREFIX}{_python_name(hook)}_{hook_idx}"

    if obj_name and "<locals>" in obj_name:
        raise ValueError("functions defined in local scopes are not yet supported.")
    if not mod_name:
        raise AttributeError(f"could not get resolvable python name for {obj}")
    pyname = f"{mod_name}:{obj_name}"
    if import_python_name(pyname) is not obj:  # pragma: no cover
        raise AttributeError(f"could not get resolvable python name for {obj}")
    return pyname


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
    if not path.is_dir() and dist.files:
        for f_path in dist.files:
            if "__editable__" in f_path.name:
                path = Path(f_path.read_text().strip()) / top_module
                break

    assert path.is_dir(), f"Could not find top level module {top_module} using {path}"
    return path


def convert_repository(
    path: Union[Path, str], mf_name: str = "napari.yaml", dry_run=False
) -> Tuple[PluginManifest, Path]:
    """Convert repository at `path` to new npe2 style."""
    path = Path(path)

    # get the info we need and create a manifest
    info = get_package_dir_info(path)
    if not (info.package_name and info._ep1):
        msg = f'Could not detect first gen napari plugin package at "{path}".'
        if info._ep2 is not None:
            msg += f" Found a {NPE2_EP} entry_point. Is this package already converted?"
        raise ValueError(msg)

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
""",
            stacklevel=2,
        )

    # write the yaml to top_module/napari.yaml
    mf_path.write_text(manifest.yaml())
    return manifest, mf_path


def _write_new_setup_cfg_ep(info: PackageInfo, mf_name: str):
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


def _guess_fname_patterns(func):
    """Try to guess filename extension patterns from source code.  Fallback to "*"."""

    patterns = ["*"]
    # try to look at source code to guess file extensions
    _, *b = inspect.getsource(func).split("endswith(")
    if b:
        try:
            middle = b[0].split(")")[0]
            if middle.startswith("("):
                middle += ")"
            files = ast.literal_eval(middle)
            if isinstance(files, str):
                files = [files]
            if files:
                patterns = [f"*{f}" for f in files]
        except Exception:  # pragma: no cover
            # couldn't do it... just accept all filename patterns
            pass
    return patterns
