from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    SupportsInt,
    Tuple,
    TypeVar,
    Union,
)

from ..types import PythonName

if TYPE_CHECKING:
    from typing_extensions import Protocol

    from .._command_registry import CommandRegistry

    class ProvidesCommand(Protocol):
        command: str

        def get_callable(self, _registry: Optional[CommandRegistry] = None):
            ...


R = TypeVar("R")


# TODO: add ParamSpec when it's supported better by mypy
class Executable(Generic[R]):
    command: str

    def exec(
        self: ProvidesCommand,
        args: tuple = (),
        kwargs: dict = {},
        _registry: Optional[CommandRegistry] = None,
    ) -> R:
        return self.get_callable(_registry)(*args, **kwargs)

    def get_callable(
        self: ProvidesCommand,
        _registry: Optional[CommandRegistry] = None,
    ) -> Callable[..., R]:
        if _registry is None:
            from .._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.get(self.command)

    @property
    def plugin_name(self: ProvidesCommand):
        # takes advantage of the fact that command always starts with manifest.name
        return self.command.split(".")[0]


@total_ordering
@dataclass
class Version:
    """A semver compatible version class.

    mostly vendored from python-semver (BSD-3):
    https://github.com/python-semver/python-semver/
    """

    major: SupportsInt
    minor: SupportsInt = 0
    patch: SupportsInt = 0
    prerelease: Union[bytes, str, int, None] = None
    build: Union[bytes, str, int, None] = None

    _SEMVER_PATTERN = re.compile(
        r"""
            ^
            (?P<major>0|[1-9]\d*)
            \.
            (?P<minor>0|[1-9]\d*)
            \.
            (?P<patch>0|[1-9]\d*)
            (?:-(?P<prerelease>
                (?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
                (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*
            ))?
            (?:\+(?P<build>
                [0-9a-zA-Z-]+
                (?:\.[0-9a-zA-Z-]+)*
            ))?
            $
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(cls, version: Union[bytes, str]) -> Version:
        """Convert string or bytes into Version object."""
        if isinstance(version, bytes):
            version = version.decode("UTF-8")
        match = cls._SEMVER_PATTERN.match(version)
        if match is None:
            raise ValueError(f"{version} is not valid SemVer string")
        matched_version_parts: Dict[str, Any] = match.groupdict()
        return cls(**matched_version_parts)

    # NOTE: we're only comparing the numeric parts for now.
    # ALSO: the rest of the comparators come  from functools.total_ordering
    def __eq__(self, other) -> bool:
        return self.to_tuple()[:3] == self._from_obj(other).to_tuple()[:3]

    def __lt__(self, other) -> bool:
        return self.to_tuple()[:3] < self._from_obj(other).to_tuple()[:3]

    @classmethod
    def _from_obj(cls, other):
        if isinstance(other, (str, bytes)):
            other = Version.parse(other)
        elif isinstance(other, dict):
            other = Version(**other)
        elif isinstance(other, (tuple, list)):
            other = Version(*other)
        elif not isinstance(other, Version):
            raise TypeError(
                f"Expected str, bytes, dict, tuple, list, or {cls} instance, "
                f"but got {type(other)}"
            )
        return other

    def to_tuple(self) -> Tuple[int, int, int, Optional[str], Optional[str]]:
        """Return version as tuple (first three are int, last two Opt[str])."""
        return (
            int(self.major),
            int(self.minor),
            int(self.patch),
            str(self.prerelease) if self.prerelease is not None else None,
            str(self.build) if self.build is not None else None,
        )

    def __iter__(self):
        yield from self.to_tuple()

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:  # pragma: no cover
            v += str(self.prerelease)
        if self.build:  # pragma: no cover
            v += str(self.build)
        return v


def import_python_name(python_name: PythonName) -> Any:
    from importlib import import_module

    from ._validators import PYTHON_NAME_PATTERN

    match = PYTHON_NAME_PATTERN.match(python_name)
    if not match:  # pragma: no cover
        raise ValueError(f"Invalid python name: {python_name}")

    module_name, funcname = match.groups()

    mod = import_module(module_name)
    return getattr(mod, funcname)
