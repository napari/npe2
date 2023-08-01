import ast
import inspect
from abc import ABC, abstractmethod
from importlib.metadata import Distribution
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Tuple, Type, Union

from npe2.manifest import contributions

if TYPE_CHECKING:
    from pydantic import BaseModel


CONTRIB_MAP: Dict[str, Tuple[Type["BaseModel"], str]] = {
    "writer": (contributions.WriterContribution, "writers"),
    "reader": (contributions.ReaderContribution, "readers"),
    "sample_data_generator": (contributions.SampleDataGenerator, "sample_data"),
    "widget": (contributions.WidgetContribution, "widgets"),
}


class _DecoratorVisitor(ast.NodeVisitor, ABC):
    """Visitor that finds decorators that match something.

    1. Visit all `Import` and `ImportFrom` nodes in the module, storing their import
       names in `_names` so we can look them up later.  For example, if the module
       had the line `from npe2 import implements as impls` at the top, then the
       `visit_ImportFrom` method would add the entry:
       `self._names['impls'] = 'npe2.implements'`
       This way, we know that an `@impls` found later in the module is referring to
       `npe2.implements`.
    2. Visit all `FunctionDef` and `ClassDef` nodes in the module and check their
       decorators with `_find_decorators`
    3. In `_find_decorators` we check to see if the name of any of the decorators
       resolves to the something from self._match (i.e., if it's being decorated
       with something from `npe2.implements`).  If it is, then we call
       `_process_decorated`

    implement `_process_decorated` in subclasses
    """

    def __init__(self, module_name: str, match: str) -> None:
        self.module_name = module_name
        self._match = match
        self._names: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> Any:
        # https://docs.python.org/3/library/ast.html#ast.Import
        for alias in node.names:
            self._names[alias.asname or alias.name] = alias.name
        return super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        # https://docs.python.org/3/library/ast.html#ast.ImportFrom
        module = node.module
        if node.level > 0:
            root = self.module_name.rsplit(".", node.level)[0]
            module = f"{root}.{module}"
        for alias in node.names:
            self._names[alias.asname or alias.name] = f"{module}.{alias.name}"
        return super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        # https://docs.python.org/3/library/ast.html#ast.FunctionDef
        self._find_decorators(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._find_decorators(node)

    def _find_decorators(self, node: Union[ast.ClassDef, ast.FunctionDef]):
        # for each in the decorator list ...
        for call in node.decorator_list:
            # https://docs.python.org/3/library/ast.html#ast.Call
            if isinstance(call, ast.Name) and self._names.get(call.id, "").startswith(
                self._match
            ):
                self._process_decorated(call.id, node, {})

            if not isinstance(call, ast.Call):
                continue
            # if the function is an attribute ...
            # (e.g in `@npe2.implements.reader`, `reader` is an attribute of
            # implements, which is an attribute of npe2)
            if isinstance(call.func, ast.Attribute):
                # then go up the chain of attributes until we get to a root Name
                val = call.func.value
                _names = []
                while isinstance(val, ast.Attribute):
                    _names.append(val.attr)
                    val = val.value
                if isinstance(val, ast.Name):
                    _names.append(val.id)
                    # finally, we can build the fully resolved call name of the
                    # decorator (e.g. `@npe2.implements`, or `@implements`)
                    call_name = ".".join(reversed(_names))
                    # we then check the `_names` we gathered during imports to resolve
                    # these call names to their fully qualified names (e.g. `implements`
                    # would resolve to `npe2.implements` if the name `implements` was
                    # imported from `npe2`.)
                    # If the name resolves to whatever `self._match` is,
                    # then we have a hit! process the function.
                    # In the case of an NPE2 module visitor, the name we're trying to
                    # match will be `npe2.implements` or `implements`.
                    # In the case of a npe1 visitor, the name we're trying to match
                    # will be `napari_plugin_engine.napari_hook_implementation`.
                    if self._names.get(call_name) == self._match:
                        kwargs = self._keywords_to_kwargs(call.keywords)
                        self._process_decorated(call.func.attr, node, kwargs)
            elif isinstance(call.func, ast.Name):
                # if the function is just a direct name (e.g. `@reader`)
                # then we can just see if the name points to something imported from
                # this module.
                if self._names.get(call.func.id, "").startswith(self._match):
                    kwargs = self._keywords_to_kwargs(call.keywords)
                    self._process_decorated(call.func.id, node, kwargs)
        return super().generic_visit(node)

    def _keywords_to_kwargs(self, keywords: List[ast.keyword]) -> Dict[str, Any]:
        return {str(k.arg): ast.literal_eval(k.value) for k in keywords}

    @abstractmethod
    def _process_decorated(
        self,
        decorator_name: str,
        node: Union[ast.ClassDef, ast.FunctionDef],
        decorator_kwargs: dict,
    ):
        """Process a decorated function.

        This is a hook for subclasses to do something with the decorated function.
        """


class NPE2PluginModuleVisitor(_DecoratorVisitor):
    """AST visitor to find all contributions in an npe2 module.

    This visitor will find all the contributions (things decorated with
    `@npe2.implements`) in a module and store them in `contribution_points`.

    It works as follows:

    See how decorators are found in the docstring for `_DecoratorVisitor`.
    when a decorator is found that matches `npe2.implements` (e.g. `@implements.reader`)

    4. `_store_contrib` first calls `_store_command` which does the job of storing the
       fully-resolved `python_name` for the function being decorated, and creates a
       CommandContribution. `_store_contrib` will then create the appropriate
       contribution type (e.g. `npe2.implements.reader` will instantiate a
       `ReaderContribution`), set its `command` entry to the `id` of the just-created
       `CommandContribution`, then store it in `contribution_points`.
    5. When the visitor is finished, we can create an instance of `ContributionPoints`
       using `ContributionPoints(**visitor.contribution_points)`, then add it to a
       manifest.
    """

    def __init__(
        self, plugin_name: str, module_name: str, match: str = "npe2.implements"
    ) -> None:
        super().__init__(module_name, match)
        self.plugin_name = plugin_name
        self.contribution_points: Dict[str, List[dict]] = {}

    def _process_decorated(
        self,
        decorator_name: str,
        node: Union[ast.ClassDef, ast.FunctionDef],
        decorator_kwargs: dict,
    ):
        self._store_contrib(decorator_name, node.name, decorator_kwargs)

    def _store_contrib(self, contrib_type: str, name: str, kwargs: Dict[str, Any]):
        from npe2.implements import CHECK_ARGS_PARAM  # circ import

        kwargs.pop(CHECK_ARGS_PARAM, None)
        ContribClass, contrib_name = CONTRIB_MAP[contrib_type]
        contrib = ContribClass(**self._store_command(name, kwargs))
        existing: List[dict] = self.contribution_points.setdefault(contrib_name, [])
        existing.append(contrib.dict(exclude_unset=True))

    def _store_command(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        cmd_params = inspect.signature(contributions.CommandContribution).parameters

        cmd_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in cmd_params}
        cmd_kwargs["python_name"] = self._qualified_pyname(name)
        cmd = contributions.CommandContribution(**cmd_kwargs)
        if cmd.id.startswith(self.plugin_name):
            n = len(self.plugin_name)
            cmd.id = cmd.id[n:]
        cmd.id = f"{self.plugin_name}.{cmd.id.lstrip('.')}"
        cmd_contribs: List[dict] = self.contribution_points.setdefault("commands", [])
        cmd_contribs.append(cmd.dict(exclude_unset=True))
        kwargs["command"] = cmd.id
        return kwargs

    def _qualified_pyname(self, obj_name: str) -> str:
        return f"{self.module_name}:{obj_name}"


class NPE1PluginModuleVisitor(_DecoratorVisitor):
    """AST visitor to find all contributions in an npe1 module."""

    def __init__(self, plugin_name: str, module_name: str) -> None:
        super().__init__(module_name, "napari_plugin_engine.napari_hook_implementation")
        self.plugin_name = plugin_name
        self.contribution_points: DefaultDict[str, list] = DefaultDict(list)

    def _process_decorated(
        self,
        decorator_name: str,
        node: Union[ast.ClassDef, ast.FunctionDef],
        decorator_kwargs: Dict[str, Any],
    ):
        self.generic_visit(node)  # do this to process any imports in the function
        hookname = decorator_kwargs.get("specname", node.name)
        getattr(self, hookname)(node)

    def _add_command(self, node: ast.FunctionDef) -> contributions.CommandContribution:
        cmd_id = f"{self.plugin_name}.{node.name}"
        py_name = f"{self.module_name}:{node.name}"
        cmd_contrib = contributions.CommandContribution(
            id=cmd_id, python_name=py_name, title=node.name
        )
        self.contribution_points["commands"].append(cmd_contrib)
        return cmd_contrib

    def napari_get_reader(self, node: ast.FunctionDef):
        cmd = self._add_command(node)
        rdr_contrib = contributions.ReaderContribution(
            command=cmd.id, filename_patterns=["*"], accepts_directories=True
        )
        self.contribution_points["readers"].append(rdr_contrib)

    def napari_get_writer(self, node: ast.FunctionDef):
        # we can't convert this to an npe2 command contribution
        pass  # pragma: no cover

    def napari_write_graph(self, node: ast.FunctionDef):
        self._parse_writer(node, "graph")  # pragma: no cover

    def napari_write_image(self, node: ast.FunctionDef):
        self._parse_writer(node, "image")

    def napari_write_labels(self, node: ast.FunctionDef):
        self._parse_writer(node, "labels")  # pragma: no cover

    def napari_write_points(self, node: ast.FunctionDef):
        self._parse_writer(node, "points")  # pragma: no cover

    def napari_write_shapes(self, node: ast.FunctionDef):
        self._parse_writer(node, "shapes")  # pragma: no cover

    def napari_write_vectors(self, node: ast.FunctionDef):
        self._parse_writer(node, "vectors")  # pragma: no cover

    def _parse_writer(self, node, layer_type: str):
        cmd = self._add_command(node)
        wrt_contrib = contributions.WriterContribution(
            command=cmd.id, layer_types=[layer_type], display_name=layer_type
        )
        self.contribution_points["writers"].append(wrt_contrib)

    def napari_provide_sample_data(self, node: ast.FunctionDef):
        from npe2.manifest.utils import safe_key

        return_ = next(n for n in node.body if isinstance(n, ast.Return))
        if not isinstance(return_.value, ast.Dict):
            raise TypeError(  # pragma: no cover
                f"napari_provide_sample_data must return a dict, not {type(return_)}"
            )

        contrib: contributions.SampleDataContribution
        for key, val in zip(return_.value.keys, return_.value.values):
            if isinstance(val, ast.Dict):
                raise NotImplementedError("npe1 sample dicts-of-dicts not supported")

            assert isinstance(key, ast.Constant)
            display_name = key.value
            key = safe_key(display_name)  # type: ignore

            # sample should now either be a callable, or a string
            if isinstance(val, ast.Name):
                cmd_id = f"{self.plugin_name}.{val.id}"
                py_name = f"{self.module_name}:{val.id}"
                cmd_contrib = contributions.CommandContribution(
                    id=cmd_id, python_name=py_name, title=val.id
                )
                self.contribution_points["commands"].append(cmd_contrib)
                contrib = contributions.SampleDataGenerator(
                    command=cmd_id, key=key, display_name=display_name
                )
            else:
                uri = "__dynamic__"  # TODO: make this a real uri
                contrib = contributions.SampleDataURI(
                    key=key, display_name=display_name, uri=uri
                )

            self.contribution_points["sample_data"].append(contrib)

    def napari_experimental_provide_function(self, node: ast.FunctionDef):
        return_ = next(n for n in node.body if isinstance(n, ast.Return))

        items = (
            list(return_.value.elts)
            if isinstance(return_.value, ast.List)
            else [return_.value]  # type: ignore
        )

        for item in items:
            if not isinstance(item, ast.Name):
                raise NotImplementedError(  # pragma: no cover
                    "provide function got non-name"
                )

            py_name = self._names.get(item.id)
            py_name = (
                ":".join(py_name.rsplit(".", 1))
                if py_name
                else f"{self.module_name}:{node.name}"
            )

            cmd_id = f"{self.plugin_name}.{node.name}"
            cmd_contrib = contributions.CommandContribution(
                id=cmd_id, python_name=py_name, title=item.id
            )

            wdg_contrib = contributions.WidgetContribution(
                command=cmd_id, display_name=item.id, autogenerate=True
            )
            self.contribution_points["commands"].append(cmd_contrib)
            self.contribution_points["widgets"].append(wdg_contrib)

    def napari_experimental_provide_dock_widget(self, node: ast.FunctionDef):
        return_ = next(n for n in node.body if isinstance(n, ast.Return))
        items = (
            list(return_.value.elts)
            if isinstance(return_.value, ast.List)
            else [return_.value]  # type: ignore
        )

        for item in items:
            wdg_creator = item.elts[0] if isinstance(item, ast.Tuple) else item
            if isinstance(wdg_creator, ast.Name):
                # eg `SegmentationWidget`
                obj_name = wdg_creator.id
                if py_name := self._names.get(wdg_creator.id):
                    py_name = ":".join(py_name.rsplit(".", 1))
                else:
                    py_name = f"{self.module_name}:{obj_name}"
            elif isinstance(wdg_creator, ast.Attribute):
                # eg `measurement.analyze_points_layer`
                py_name = wdg_creator.attr
                tmp = wdg_creator
                assert isinstance(tmp.value, ast.Name)
                py_name = f"{self._names[tmp.value.id]}.{py_name}"
                py_name = ":".join(py_name.rsplit(".", 1))
                obj_name = tmp.value.id
            else:
                raise TypeError(  # pragma: no cover
                    f"Unexpected widget creator type: {type(wdg_creator)}"
                )

            cmd_id = f"{self.plugin_name}.{obj_name}"
            cmd_contrib = contributions.CommandContribution(
                id=cmd_id, python_name=py_name, title=obj_name
            )
            wdg_contrib = contributions.WidgetContribution(
                command=cmd_id, display_name=obj_name
            )
            self.contribution_points["commands"].append(cmd_contrib)
            self.contribution_points["widgets"].append(wdg_contrib)


def find_npe2_module_contributions(
    path: Union[ModuleType, str, Path], plugin_name: str, module_name: str = ""
) -> contributions.ContributionPoints:
    """Visit an npe2 module and extract contribution points.

    Parameters
    ----------
    path : Union[ModuleType, str, Path]
        Either a path to a Python module, a module object, or a string
    plugin_name : str
        Name of the plugin
    module_name : str
        Module name, by default ""

    Returns
    -------
    ContributionPoints
        ContributionPoints discovered in the module.
    """
    if isinstance(path, ModuleType):
        assert path.__file__
        assert path.__name__
        module_name = path.__name__
        path = path.__file__

    visitor = NPE2PluginModuleVisitor(plugin_name, module_name=module_name)
    visitor.visit(ast.parse(Path(path).read_text()))
    if "commands" in visitor.contribution_points:
        compress = {tuple(i.items()) for i in visitor.contribution_points["commands"]}
        visitor.contribution_points["commands"] = [dict(i) for i in compress]
    return contributions.ContributionPoints(**visitor.contribution_points)


def find_npe1_module_contributions(
    dist: Distribution, module_name: str = ""
) -> contributions.ContributionPoints:
    """Statically visit an npe1 module and extract contribution points.

    Parameters
    ----------
    dist: Distribution
        A distribution object representing an npe1 plugin to be visited.
    module_name : str
        Module name, by default ""

    Returns
    -------
    ContributionPoints
        ContributionPoints discovered in the module.
    """
    plugin_name = dist.metadata["Name"]
    file = _locate_module_in_dist(dist, module_name)
    visitor = NPE1PluginModuleVisitor(plugin_name, module_name=module_name)
    visitor.visit(ast.parse(Path(file).read_text()))

    # now check all of the modules that were imported by `module_name` to see
    # if any of those had npe1 decorated functions.
    # NOTE: we're only going 1 level deep here...
    for name, target in visitor._names.items():
        if not name.startswith("_"):
            target_module = target.rsplit(".", 1)[0]
            try:
                file = _locate_module_in_dist(dist, target_module)
            except FileNotFoundError:
                # if the imported module is not in the same distribution
                # just skip it.
                continue
            # NOTE: technically, this time we should restrict the allowable names
            # to those that are imported from the original module_name ...
            # but that's probably overkill
            v2 = NPE1PluginModuleVisitor(plugin_name, target_module)
            v2.visit(ast.parse(file.read_text()))
            visitor.contribution_points.update(v2.contribution_points)

    return contributions.ContributionPoints(**visitor.contribution_points)


def _locate_module_in_dist(dist: Distribution, module_name: str) -> Path:
    root = dist.locate_file(module_name.replace(".", "/"))
    assert isinstance(root, Path)

    if not (file := root / "__init__.py").exists():
        if not (file := root.with_suffix(".py")).exists():
            raise FileNotFoundError(
                f"Could not find {module_name!r} in "
                f"in distribution for {dist.metadata['Name']}"
            )
    return file
