"""
# pyproject.toml
[build-system]
requires = ["setuptools", "wheel", "setuptools_scm", "npe2"]
build-backend = "setuptools.build_meta"

[tool.npe2]
"""
from __future__ import annotations

import os
import re
import sys
import warnings
from typing import TYPE_CHECKING, Optional, Tuple, cast

from setuptools import Distribution
from setuptools.command.build_py import build_py

if TYPE_CHECKING:
    from distutils.cmd import Command
    from typing import Any, Union

    PathT = Union["os.PathLike[str]", str]

NPE2_ENTRY = "napari.manifest"
DEBUG = bool(os.environ.get("SETUPTOOLS_NPE2_DEBUG"))
EP_PATTERN = re.compile(
    r"(?P<module>[\w.]+)\s*(:\s*(?P<attr>[\w.]+)\s*)?((?P<extras>\[.*\])\s*)?$"
)


def trace(*k: object) -> None:
    if DEBUG:
        print(*k, file=sys.stderr, flush=True)


def _lazy_tomli_load(data: str) -> dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore [no-redef]

    return tomllib.loads(data)


def _read_dist_name_from_setup_cfg() -> str | None:
    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read(["setup.cfg"])
    return parser.get("metadata", "name", fallback=None)


def _check_absolute_root(root: PathT, relative_to: PathT | None) -> str:
    trace("abs root", repr(locals()))
    if relative_to:
        if (
            os.path.isabs(root)
            and os.path.commonpath([root, relative_to]) != relative_to
        ):
            warnings.warn(
                f"absolute root path '{root}' overrides relative_to '{relative_to}'",
                stacklevel=2,
            )
        if os.path.isdir(relative_to):
            warnings.warn(
                "relative_to is expected to be a file,"
                " its the directory {relative_to!r}\n"
                "assuming the parent directory was passed",
                stacklevel=2,
            )
            trace("dir", relative_to)
            root = os.path.join(relative_to, root)
        else:
            trace("file", relative_to)
            root = os.path.join(os.path.dirname(relative_to), root)
    return os.path.abspath(root)


class Configuration:
    """Global configuration model"""

    def __init__(
        self,
        relative_to: PathT | None = None,
        root: PathT = ".",
        write_to: PathT | None = None,
        write_to_template: str | None = None,
        dist_name: str | None = None,
        template: str | None = None,
    ):
        self._relative_to = None if relative_to is None else os.fspath(relative_to)
        self._root = "."
        self.root = os.fspath(root)
        self.write_to = write_to
        self.write_to_template = write_to_template
        self.dist_name = dist_name
        self.template = template

    @property
    def relative_to(self) -> str | None:
        return self._relative_to

    @property
    def root(self) -> str:
        return self._root

    @root.setter
    def root(self, value: PathT) -> None:
        self._absolute_root = _check_absolute_root(value, self._relative_to)
        self._root = os.fspath(value)
        trace("root", repr(self._absolute_root))
        trace("relative_to", repr(self._relative_to))

    @property
    def absolute_root(self) -> str:
        return self._absolute_root

    @classmethod
    def from_file(
        cls, name: str = "pyproject.toml", dist_name: str | None = None, **kwargs: Any
    ) -> Configuration:
        """
        Read Configuration from pyproject.toml (or similar).
        Raises exceptions when file is not found or toml is
        not installed or the file has invalid format or does
        not contain the [tool.npe2] section.
        """

        with open(name, encoding="UTF-8") as strm:
            data = strm.read()
        defn = _lazy_tomli_load(data)
        try:
            section = defn.get("tool", {})["npe2"]
        except LookupError as e:
            raise LookupError(f"{name} does not contain a tool.npe2 section") from e
        if "dist_name" in section:
            if dist_name is None:
                dist_name = section.pop("dist_name")
            else:
                assert dist_name == section["dist_name"]
                del section["dist_name"]
        if dist_name is None and "project" in defn:
            # minimal pep 621 support for figuring the pretend keys
            dist_name = defn["project"].get("name")
        if dist_name is None:
            dist_name = _read_dist_name_from_setup_cfg()

        return cls(dist_name=dist_name, **section, **kwargs)


def _mf_entry_from_dist(dist: Distribution) -> Optional[Tuple[str, str]]:
    """Return (module, attr) for a distribution's npe2 entry point."""
    eps: dict = getattr(dist, "entry_points", {})
    if napari_entrys := eps.get(NPE2_ENTRY, []):
        if match := EP_PATTERN.search(napari_entrys[0]):
            return match.group("module"), match.group("attr")
    return None


class npe2_compile(build_py):
    def run(self) -> None:
        trace("RUN npe2_compile")
        if ep := _mf_entry_from_dist(self.distribution):
            from npe2._inspection._compile import compile

            module, attr = ep
            src = self.distribution.src_root or os.getcwd()
            dest = os.path.join(self.get_package_dir(module), attr)
            compile(src, dest, template=self.distribution.config.template)
        else:
            name = self.distribution.metadata.name
            trace(f"no {NPE2_ENTRY!r} found in entry_points for {name}")


def finalize_npe2(dist: Distribution):
    # this hook is declared in the setuptools.finalize_distribution_options
    # entry point in our setup.cfg
    # https://setuptools.pypa.io/en/latest/userguide/extension.html#customizing-distribution-options
    trace("finalize hook", vars(dist.metadata))
    dist_name = dist.metadata.name
    if dist_name is None:
        dist_name = _read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "npe2":
        # if we're packaging npe2 itself, don't do anything
        return
    try:
        # config will *only* be detected if there is a [tool.npe2]
        # section in pyproject.toml.  This is how plugins opt in
        # to the npe2 compile feature during build
        config = Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        trace(e)
    else:
        # inject our `npe2_compile` command to be called whenever we're building an
        # sdist or a wheel
        dist.config = config
        for cmd in ("build", "sdist"):
            if base := dist.get_command_class(cmd):
                cast("Command", base).sub_commands.insert(0, ("npe2_compile", None))
