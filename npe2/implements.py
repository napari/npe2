import ast
import contextlib
import inspect
from inspect import Parameter, Signature
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Sequence, Tuple, Type, TypeVar, Union

from pydantic import BaseModel

from .manifest import contributions

__all__ = [
    "on_activate",
    "on_deactivate",
    "PluginModuleVisitor",
    "reader",
    "sample_data_generator",
    "visit",
    "widget",
    "writer",
]

T = TypeVar("T", bound=Callable[..., Any])
_COMMAND_PARAMS = inspect.signature(contributions.CommandContribution).parameters
CONTRIB_MAP: Dict[str, Tuple[Type[BaseModel], str]] = {
    "writer": (contributions.WriterContribution, "writers"),
    "reader": (contributions.ReaderContribution, "readers"),
    "sample_data_generator": (contributions.SampleDataGenerator, "sample_data"),
    "widget": (contributions.WidgetContribution, "widgets"),
}
CHECK_ARGS_PARAM = "ensure_args_valid"


def _build_decorator(contrib: Type[BaseModel]) -> Callable:
    """Create a decorator (e.g. `@implements.reader`) to mark an object as a contrib.

    Parameters
    ----------
    contrib : Type[BaseModel]
        The type of contribution this object implements.
    """
    # build a signature based on the fields in this contribution type, mixed with
    # the fields in the CommandContribution
    contribs: Sequence[Type[BaseModel]] = (contributions.CommandContribution, contrib)
    params: List[Parameter] = []
    for contrib in contribs:
        # iterate over the fields in the contribution types
        for field in contrib.__fields__.values():
            # we don't need python_name (since that will be gleaned from the function
            # we're decorating) ... and we don't need `command`, since that will just
            # be a string pointing to the contributions.commands entry that we are
            # creating here.
            if field.name not in {"python_name", "command"}:
                # ensure that required fields raise a TypeError if they are not provided
                default = Parameter.empty if field.required else field.get_default()
                # create the parameter and add it to the signature.
                param = Parameter(
                    field.name,
                    Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=field.outer_type_ or field.type_,
                )
                params.append(param)

    # add one more parameter to control whether the arguments in the decorator itself
    # are validated at runtime
    params.append(
        Parameter(
            CHECK_ARGS_PARAM,
            kind=Parameter.KEYWORD_ONLY,
            default=False,
            annotation=bool,
        )
    )

    signature = Signature(parameters=params, return_annotation=Callable[[T], T])

    # creates the actual `@npe2.implements.something` decorator
    # this just stores the parameters for the corresponding contribution type
    # as attributes on the function being decorated.
    def _deco(**kwargs) -> Callable[[T], T]:
        def _store_attrs(func: T) -> T:
            # If requested, assert that we've satisfied the signature when
            # the decorator is invoked at runtime.
            # TODO: improve error message to provide context
            if kwargs.pop(CHECK_ARGS_PARAM, False):
                signature.bind(**kwargs)

            # TODO: check if it's already there and assert the same id
            # store these attributes on the function
            with contextlib.suppress(AttributeError):
                setattr(func, f"_npe2_{contrib.__name__}", kwargs)

            # return the original decorated function
            return func

        return _store_attrs

    # set the signature and return the decorator
    setattr(_deco, "__signature__", signature)
    return _deco


# builds decorators for each of the contribution types that are essentially just
# pointers to some command.
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


class PluginModuleVisitor(ast.NodeVisitor):
    """AST visitor to find all contributions in a module.

    This visitor will find all the contributions in a module and store them in
    `contribution_points`.  It works as follows:

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
       resolves to the something from this module (i.e., if it's being decorated with
       something from `npe2.implements`).  If it is, then we call `_store_contrib`...
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

    def __init__(self, plugin_name: str, module_name: str) -> None:
        super().__init__()
        self.plugin_name = plugin_name
        self.module_name = module_name
        self.contribution_points: Dict[str, List[dict]] = {}
        self._names: Dict[str, str] = {}

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
            # if the function is an attribute ...
            # (e.g in `@npe2.implements.reader`, `reader` is an attribute of
            # implements, which is an attribute of npe2)
            if not isinstance(call, ast.Call):
                continue
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
                    # we then check the `_names` we gathered above to resolve these
                    # call names to their fully qualified names (e.g. `implements`
                    # would resolve to `npe2.implements` if the name `implements` was
                    # imported from `npe2`.)
                    # If the name resolves to the name of this module,
                    # then we have a hit! Store the contribution.
                    if self._names.get(call_name) == __name__:
                        kwargs = self._keywords_to_kwargs(call.keywords)
                        self._store_contrib(call.func.attr, node.name, kwargs)
            elif isinstance(call.func, ast.Name):
                # if the function is just a direct name (e.g. `@reader`)
                # then we can just see if the name points to something imported from
                # this module.
                if self._names.get(call.func.id, "").startswith(__name__):
                    kwargs = self._keywords_to_kwargs(call.keywords)
                    self._store_contrib(call.func.id, node.name, kwargs)
        return super().generic_visit(node)

    def _keywords_to_kwargs(self, keywords: List[ast.keyword]) -> Dict[str, Any]:
        return {str(k.arg): ast.literal_eval(k.value) for k in keywords}

    def _store_contrib(self, contrib_type: str, name: str, kwargs: Dict[str, Any]):
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

    visitor = PluginModuleVisitor(plugin_name, module_name=module_name)
    visitor.visit(ast.parse(Path(path).read_text()))
    if "commands" in visitor.contribution_points:
        compress = {tuple(i.items()) for i in visitor.contribution_points["commands"]}
        visitor.contribution_points["commands"] = [dict(i) for i in compress]
    return contributions.ContributionPoints(**visitor.contribution_points)
