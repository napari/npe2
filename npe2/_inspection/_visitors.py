import ast
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from ..manifest import contributions

if TYPE_CHECKING:
    from pydantic import BaseModel

_COMMAND_PARAMS = inspect.signature(contributions.CommandContribution).parameters

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

    def __init__(self, match: str) -> None:
        super().__init__()
        self._names: Dict[str, str] = {}
        self._match = match

    def visit_Import(self, node: ast.Import) -> Any:  # noqa: D102
        # https://docs.python.org/3/library/ast.html#ast.Import
        for alias in node.names:
            self._names[alias.asname or alias.name] = alias.name
        return super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:  # noqa: D102
        # https://docs.python.org/3/library/ast.html#ast.ImportFrom
        for alias in node.names:
            self._names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        return super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: D102
        # https://docs.python.org/3/library/ast.html#ast.FunctionDef
        self._find_decorators(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: D102
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
                    # If the name resolves to the name of this module,
                    # then we have a hit! process the function.
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
    """AST visitor to find all contributions in a module.

    This visitor will find all the contributions in a module and store them in
    `contribution_points`.  It works as follows:

    See how decorators are found in the _DecoratorVisitor docstring.
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
        super().__init__(match)
        self.plugin_name = plugin_name
        self.module_name = module_name
        self.contribution_points: Dict[str, List[dict]] = {}

    def _process_decorated(
        self,
        decorator_name: str,
        node: Union[ast.ClassDef, ast.FunctionDef],
        decorator_kwargs: dict,
    ):
        self._store_contrib(decorator_name, node.name, decorator_kwargs)

    def _store_contrib(self, contrib_type: str, name: str, kwargs: Dict[str, Any]):
        from ..implements import CHECK_ARGS_PARAM  # circ import

        kwargs.pop(CHECK_ARGS_PARAM, None)
        ContribClass, contrib_name = CONTRIB_MAP[contrib_type]
        contrib = ContribClass(**self._store_command(name, kwargs))
        existing: List[dict] = self.contribution_points.setdefault(contrib_name, [])
        existing.append(contrib.dict(exclude_unset=True))

    def _store_command(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:

        cmd_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in _COMMAND_PARAMS}
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
    def __init__(self, plugin_name: str, module_name: str) -> None:
        super().__init__("napari_plugin_engine.napari_hook_implementation")
        self.plugin_name = plugin_name
        self.module_name = module_name
        self.contribution_points: DefaultDict[str, list] = DefaultDict(list)

    def _process_decorated(
        self,
        decorator_name: str,
        node: Union[ast.ClassDef, ast.FunctionDef],
        decorator_kwargs: Dict[str, Any],
    ):
        self.generic_visit(node)  # do this to process any imports in the function
        hookname = decorator_kwargs.get("specname", node.name)
        try:
            getattr(self, hookname)(node)  # TODO: make methods for each type
        except AttributeError:
            print(f"TODO: implement {hookname}")

    def napari_get_reader(self, node: ast.FunctionDef):
        cmd_id = f"{self.plugin_name}.{node.name}"
        py_name = f"{self.module_name}:{node.name}"
        cmd_contrib = contributions.CommandContribution(
            id=cmd_id, python_name=py_name, title=node.name
        )
        rdr_contrib = contributions.ReaderContribution(
            command=cmd_id, filename_patterns=["*"], accepts_directories=True
        )
        self.contribution_points["commands"].append(cmd_contrib)
        self.contribution_points["readers"].append(rdr_contrib)

    def napari_experimental_provide_dock_widget(self, node: ast.FunctionDef):
        return_ = next(n for n in node.body if isinstance(n, ast.Return))
        if isinstance(return_.value, ast.List):
            items: List[Optional[ast.expr]] = list(return_.value.elts)
        else:
            items = [return_.value]

        for item in items:
            wdg_creator = item.elts[0] if isinstance(item, ast.Tuple) else item
            if isinstance(wdg_creator, ast.Name):
                py_name = self._names.get(wdg_creator.id, "")
            else:
                raise TypeError(f"Unexpected widget creator type: {type(wdg_creator)}")

            py_name = ":".join(py_name.rsplit(".", 1))
            cmd_id = f"{self.plugin_name}.{wdg_creator.id}"
            cmd_contrib = contributions.CommandContribution(
                id=cmd_id, python_name=py_name, title=wdg_creator.id
            )
            wdg_contrib = contributions.WidgetContribution(
                command=cmd_id, display_name=wdg_creator.id
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
    path: Union[ModuleType, str, Path], plugin_name: str, module_name: str = ""
) -> contributions.ContributionPoints:
    """Visit an npe1 module and extract contribution points.

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

    visitor = NPE1PluginModuleVisitor(plugin_name, module_name=module_name)
    visitor.visit(ast.parse(Path(path).read_text()))
    # if "commands" in visitor.contribution_points:
    # compress = {tuple(i.items()) for i in visitor.contribution_points["commands"]}
    # visitor.contribution_points["commands"] = [dict(i) for i in compress]
    return contributions.ContributionPoints(**visitor.contribution_points)
