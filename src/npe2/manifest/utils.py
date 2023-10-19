from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from importlib import import_module
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Sequence,
    SupportsInt,
    Tuple,
    TypeVar,
    Union,
)

from npe2._pydantic_compat import GenericModel, PrivateAttr
from npe2.types import PythonName

if TYPE_CHECKING:
    from npe2._command_registry import CommandRegistry
    from npe2.manifest.schema import PluginManifest

    from .contributions import ContributionPoints


def v1_to_v2(path):
    return (path, True) if isinstance(path, list) else ([path], False)


def v2_to_v1(paths, stack):
    if stack:
        return paths
    assert len(paths) == 1
    return paths[0]


R = TypeVar("R")
SHIM_NAME_PREFIX = "__npe1shim__."


# TODO: add ParamSpec when it's supported better by mypy
class Executable(GenericModel, Generic[R]):
    command: str
    # plugin_name gets populated in `PluginManifest.__init__`
    _plugin_name: str = PrivateAttr("")

    def exec(
        self,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        _registry: Optional[CommandRegistry] = None,
    ) -> R:
        if kwargs is None:
            kwargs = {}
        reg = _registry or kwargs.pop("_registry", None)
        return self.get_callable(reg)(*args, **kwargs)

    def get_callable(
        self,
        _registry: Optional[CommandRegistry] = None,
    ) -> Callable[..., R]:
        if _registry is None:
            from npe2._plugin_manager import PluginManager

            _registry = PluginManager.instance().commands
        return _registry.get(self.command)

    @property
    def plugin_name(self) -> str:
        """Return the manifest/plugin name for this contribution."""
        if not self._plugin_name:
            # we will likely never get here if the contribution was created
            # as a member of a PluginManifest.
            # But if not, we can use a couple heuristics...
            from importlib.metadata import distributions

            # look for a package name in the command id
            dists = sorted(
                (d.metadata["Name"] for d in distributions()), key=len, reverse=True
            )
            for name in dists:
                if self.command.startswith(name):  # pragma: no cover
                    self._plugin_name = name
                    break
            else:
                # just split on the first period.
                # Will break for package names with periods
                self._plugin_name = self.command.split(".")[0]
        return self._plugin_name


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

    assert shim_name.startswith(SHIM_NAME_PREFIX), f"Invalid shim name: {shim_name}"
    python_name, idx = shim_name[13:].rsplit("_", maxsplit=1)  # TODO, make a function
    index = int(idx)

    hook = import_python_name(python_name)
    result = hook()
    if isinstance(result, dict):
        # things like sample_data hookspec return a dict, in which case we want the
        # "idxth" item in the dict (assumes ordered dict, which is safe now)
        result = list(result.values())
    if not isinstance(result, list):
        result = [result]  # pragma: no cover

    try:
        out = result[index]
    except IndexError as e:  # pragma: no cover
        raise IndexError(f"invalid npe1 shim index {index} for hook {hook}") from e

    if "dock_widget" in python_name and isinstance(out, tuple):
        return out[0]
    if "sample_data" in python_name and isinstance(out, dict):
        # this was a nested sample data
        return out.get("data")

    return out


def import_python_name(python_name: Union[PythonName, str]) -> Any:
    from . import _validators

    if python_name.startswith(SHIM_NAME_PREFIX):
        return _import_npe1_shim(python_name)

    _validators.python_name(python_name)  # shows the best error message
    match = _validators.PYTHON_NAME_PATTERN.match(python_name)
    module_name, funcname = match.groups()  # type: ignore [union-attr]

    mod = import_module(module_name)
    return getattr(mod, funcname)


def deep_update(dct: dict, merge_dct: dict, copy=True) -> dict:
    """Merge possibly nested dicts"""
    from copy import deepcopy

    _dct = deepcopy(dct) if copy else dct
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


def merge_manifests(
    manifests: Sequence[PluginManifest], overwrite=False
) -> PluginManifest:
    """Merge a sequence of PluginManifests into a single PluginManifest."""
    from npe2.manifest.schema import PluginManifest

    if not manifests:
        raise ValueError("Cannot merge empty sequence of manifests")
    if len(manifests) == 1:
        return manifests[0]

    assert len({mf.name for mf in manifests}) == 1, "All manifests must have same name"
    assert (
        len({mf.package_version for mf in manifests}) == 1
    ), "All manifests must have same version"
    if not overwrite:
        assert (
            len({mf.display_name for mf in manifests}) == 1
        ), "All manifests must have same display_name"

    mf0 = manifests[0]
    info = mf0.dict(exclude={"contributions"}, exclude_unset=True)
    info["contributions"] = merge_contributions(
        [m.contributions for m in manifests], overwrite=overwrite
    )
    return PluginManifest(**info)


# TODO: refactor this ugly thing
def merge_contributions(
    contribs: Sequence[Optional[ContributionPoints]], overwrite=False
) -> dict:
    """Merge a sequence of contribution points in a single dict.

    Parameters
    ----------
    contribs : Sequence[Optional[ContributionPoints]]
        A sequence of contribution points.  None values are ignored.
    overwrite : bool, optional
        If `True`, when existing command id's are encountered, they overwrite the
        previous command. By default (`False`), the command id is incremented until
        it is unique.

    Returns
    -------
    dict
        Kwargs that can be passed to `ContributionPoints(**kwargs)`
    """
    _contribs = [c for c in contribs if c and c.dict(exclude_unset=True)]
    if not _contribs:
        return {}  # pragma: no cover

    out_dict = _contribs[0].dict(exclude_unset=True)
    if len(_contribs) <= 1:
        # no need to merge a single contribution
        return out_dict  # pragma: no cover

    for ctrb in _contribs[1:]:
        _renames = {}
        existing_cmds = {c["id"] for c in out_dict.get("commands", {})}
        new_ctrb_dict = ctrb.dict(exclude_unset=True)
        for cmd in list(new_ctrb_dict.get("commands", ())):
            cmd_id = cmd["id"]
            if cmd_id in existing_cmds:
                if overwrite:
                    # remove existing command
                    new_ctrb_dict["commands"].remove(cmd)
                else:
                    # if we're not overwriting, we need to rename the command
                    # to avoid collisions
                    i = 1
                    while cmd_id in existing_cmds:
                        if i != 1:
                            cmd_id = cmd_id[:-2]
                        i += 1
                        cmd_id = f"{cmd_id}_{i}"
                        _renames[cmd["id"]] = cmd_id
                    cmd["id"] = cmd_id
        for key, val in new_ctrb_dict.items():
            if isinstance(val, list):
                for item in val:
                    if "command" in item:
                        cmd_id = item["command"]
                        if cmd_id in _renames:
                            cmd_id = _renames[cmd_id]
                        item["command"] = cmd_id
                    if overwrite:
                        for existing_item in list(out_dict.get(key, [])):
                            if all(item[k] == existing_item[k] for k in item):
                                out_dict[key].remove(existing_item)
        out_dict = deep_update(out_dict, new_ctrb_dict)
    return out_dict


def safe_key(key: str) -> str:
    """Remove parentheses and brackets from a string."""
    key = re.sub(r"[ -]", "_", key.lower())
    return re.sub(r"[\[\]\(\)]", "", key)
