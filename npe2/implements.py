import ast
import inspect
from inspect import Parameter, Signature
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Sequence, Tuple, Type, TypeVar, Union

from pydantic import BaseModel

from .manifest import contributions

T = TypeVar("T", bound=Callable[..., Any])


def _build_decorator(contrib: Type[BaseModel]) -> Callable:
    """Create a decorator (e.g. `@implements.reader`) to mark an object as a contrib.

    Parameters
    ----------
    contrib : Type[BaseModel]
        The type of contribution this object implements.
    """
    # build a signature for this contribution, mixed with Command params
    contribs: Sequence[Type[BaseModel]] = (contributions.CommandContribution, contrib)
    params = [
        Parameter(
            f.name,
            Parameter.KEYWORD_ONLY,
            default=Parameter.empty if f.required else f.get_default(),
            annotation=f.outer_type_ or f.type_,
        )
        for f in (f for c in contribs for f in c.__fields__.values())
        if f.name not in ("python_name", "command")
    ]
    signature = Signature(parameters=params, return_annotation=Callable[[T], T])

    # create decorator
    def _deco(**kwargs) -> Callable[[T], T]:
        def _store_attrs(func: T) -> T:
            # assert we've satisfied the signature when the decorator is invoked
            # TODO: improve error message to provide context
            signature.bind(**kwargs)

            # store these attributes on the function
            # TODO: check if it's already there and assert the same id
            setattr(func, f"_npe2_{contrib.__name__}", kwargs)
            return func

        return _store_attrs

    # set the signature and return the decorator
    setattr(_deco, "__signature__", signature)
    return _deco


reader = _build_decorator(contributions.ReaderContribution)
writer = _build_decorator(contributions.WriterContribution)
widget = _build_decorator(contributions.WidgetContribution)
sample_data_generator = _build_decorator(contributions.SampleDataGenerator)


def on_activate(func):
    """Mark a function to be called when a plugin is activated."""
    setattr(func, "npe2_on_activate", True)
    return func


def on_deactivate(func):
    """Mark a function to be called when a plugin is deactivated."""
    setattr(func, "npe2_on_deactivate", True)
    return func


_COMMAND_PARAMS = inspect.signature(contributions.CommandContribution).parameters


class PluginModuleVisitor(ast.NodeVisitor):
    """AST visitor to find all contributions in a module."""

    def __init__(self, plugin_name: str, module_name: str) -> None:
        super().__init__()
        self.plugin_name = plugin_name
        self.module_name = module_name
        self.contribution_points: Dict[str, List[dict]] = {}
        self._names: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> Any:  # noqa: D102
        for alias in node.names:
            self._names[alias.asname or alias.name] = alias.name
        return super().generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:  # noqa: D102
        for alias in node.names:
            self._names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        return super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: D102
        self._find_decorators(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: D102
        self._find_decorators(node)

    def _find_decorators(self, node: Union[ast.ClassDef, ast.FunctionDef]):
        for call in node.decorator_list:
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                val = call.func.value
                _names = []
                while isinstance(val, ast.Attribute):
                    _names.append(val.attr)
                    val = val.value
                if isinstance(val, ast.Name):
                    _names.append(val.id)
                    call_name = ".".join(reversed(_names))
                    if self._names.get(call_name) == __name__:
                        self._store_contrib(call.func.attr, call.keywords, node.name)
        return super().generic_visit(node)

    def _store_contrib(self, type_: str, keywords: List[ast.keyword], name: str):
        # this can also be taken from schemas
        _map: Dict[str, Tuple[Type[BaseModel], str]] = {
            "writer": (contributions.WriterContribution, "writers"),
            "reader": (contributions.ReaderContribution, "readers"),
            "sample_data_generator": (contributions.SampleDataGenerator, "sample_data"),
            "widget": (contributions.WidgetContribution, "widgets"),
        }
        Cls, contrib_name = _map[type_]
        contrib = Cls(**self._store_command(keywords, name))
        existing: List[dict] = self.contribution_points.setdefault(contrib_name, [])
        existing.append(contrib.dict(exclude_unset=True))

    def _store_command(self, keywords: List[ast.keyword], name: str) -> Dict[str, Any]:
        kwargs = {str(k.arg): ast.literal_eval(k.value) for k in keywords}
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


def visit(
    path: Union[ModuleType, str, Path], plugin_name: str, module_name: str = ""
) -> contributions.ContributionPoints:
    """Visit a module and extract contribution points.

    Parameters
    ----------
    path : Union[ModuleType, str, Path]
        Either a path to a Python module, a module object, or a string
    plugin_name : str
        Name of the plugin
    module_name : str, optional
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

    visitor = PluginModuleVisitor(plugin_name, module_name=module_name)
    visitor.visit(ast.parse(Path(path).read_text()))
    if "commands" in visitor.contribution_points:
        compress = {tuple(i.items()) for i in visitor.contribution_points["commands"]}
        visitor.contribution_points["commands"] = [dict(i) for i in compress]
    return contributions.ContributionPoints(**visitor.contribution_points)
