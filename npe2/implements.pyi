# flake8: noqa
import ast
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, TypeVar, Union

from _typeshed import Incomplete
from pydantic import BaseModel as BaseModel

from .manifest import contributions as contributions

T = TypeVar("T", bound=Callable[..., Any])

def reader(
    *,
    id: str,
    title: str,
    filename_patterns: List[str],
    accepts_directories: bool = False,
    ensure_args_valid: bool = False,
) -> Callable[[T], T]:
    """Mark a function as a reader contribution"""

def writer(
    *,
    id: str,
    title: str,
    layer_types: List[str],
    filename_extensions: List[str] = [],
    display_name: str = "",
    ensure_args_valid: bool = False,
) -> Callable[[T], T]:
    """Mark function as a writer contribution"""

def widget(
    *,
    id: str,
    title: str,
    display_name: str,
    autogenerate: bool = False,
    ensure_args_valid: bool = False,
) -> Callable[[T], T]:
    """Mark a function as a widget contribution"""

def sample_data_generator(
    *,
    id: str,
    title: str,
    key: str,
    display_name: str,
    ensure_args_valid: bool = False,
) -> Callable[[T], T]:
    """Mark a function as a sample data generator contribution"""

def on_activate(func):
    """Mark a function to be called when a plugin is activated."""

def on_deactivate(func):
    """Mark a function to be called when a plugin is deactivated."""

class PluginModuleVisitor(ast.NodeVisitor):
    """AST visitor to find all contributions in a module."""

    plugin_name: str
    module_name: str
    contribution_points: Dict[str, List[dict]]
    def __init__(self, plugin_name: str, module_name: str) -> None: ...
    def visit_Import(self, node: ast.Import) -> Any: ...
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any: ...
    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any: ...
    def visit_ClassDef(self, node: ast.ClassDef) -> Any: ...

def visit(
    path: Union[ModuleType, str, Path], plugin_name: str, module_name: str = ...
) -> contributions.ContributionPoints:
    """Visit a module and extract contribution points."""
