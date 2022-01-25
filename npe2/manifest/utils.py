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
    from .contributions import ContributionPoints

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


def _import_npe1_shim(shim_name: str) -> Any:
    """Import npe1 shimmed python_name

    Some objects returned by npe1 hooks (such as locally defined partials or other
    objects) don't have globally accessible python names. In such cases, we create
    a "shim" python_name of the form:

    `__npe1shim__.<hook_python_name>_<index>`

    The implication is that the hook should be imported, called, and indexed to return
    the corresponding item in the hook results.

    Parameters
    ----------
    shim_name : str
        A string in the form `__npe1shim__.<hook_python_name>_<index>`

    Returns
    -------
    Any
        The <index>th object returned from the callable <hook_python_name>.

    Raises
    ------
    IndexError
        If len(<hook_python_name>()) <= <index>
    """
    assert shim_name.startswith("__npe1shim__."), "Invalid shim name"
    python_name, idx = shim_name[13:].rsplit("_", maxsplit=1)
    index = int(idx)

    hook = import_python_name(python_name)
    result = hook()
    if not isinstance(result, list):
        result = [result]
    try:
        return result[index]
    except IndexError:
        raise IndexError(f"invalid npe1 shim index {index} for hook {hook}")


def import_python_name(python_name: Union[PythonName, str]) -> Any:
    from importlib import import_module

    from . import _validators

    if python_name.startswith("__npe1shim__."):
        return _import_npe1_shim(python_name)

    _validators.python_name(python_name)  # shows the best error message
    match = _validators.PYTHON_NAME_PATTERN.match(python_name)
    module_name, funcname = match.groups()  # type: ignore [union-attr]

    mod = import_module(module_name)
    return getattr(mod, funcname)


def deep_update(dct: dict, merge_dct: dict, copy=True) -> dict:
    """Merge possibly nested dicts"""
    _dct = dct.copy() if copy else dct
    for k, v in merge_dct.items():
        if k in _dct and isinstance(dct[k], dict) and isinstance(v, dict):
            deep_update(_dct[k], v, copy=False)
        elif isinstance(v, list):
            if k not in _dct:
                _dct[k] = []
            _dct[k].extend(v)
        else:
            _dct[k] = v
    return _dct


def merge_contributions(*contribs: ContributionPoints) -> dict:
    if not contribs:
        return {}

    out = contribs[0].dict(exclude_unset=True)
    if len(contribs) > 1:
        for n, c in enumerate(contribs[1:]):
            for cmd in c.commands or ():
                cmd.id += f"_{n + 2}"
            for name, val in c:
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, Executable):
                            item.command += f"_{n + 2}"
            deep_update(out, c.dict(exclude_unset=True))
    return out
