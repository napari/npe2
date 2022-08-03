# flake8: noqa
from typing import Any, Callable, List, TypeVar

from pydantic import BaseModel as BaseModel

from .manifest import PluginManifest as PluginManifest
from .manifest import contributions as contributions

T = TypeVar("T", bound=Callable[..., Any])

CHECK_ARGS_PARAM: str

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
