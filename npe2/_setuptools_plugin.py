"""package description."""
from __future__ import annotations
from typing import TYPE_CHECKING

from setuptools import Command, Distribution
import os

if TYPE_CHECKING:
    from typing import Union, Any

    PathT = Union["os.PathLike[str]", str]


def _lazy_tomli_load(data: str) -> dict[str, Any]:
    from tomli import loads

    return loads(data)


class Configuration:
    """Global configuration model"""

    parent: PathT | None
    _root: str
    _relative_to: str | None

    def __init__(
        self,
        relative_to: PathT | None = None,
        root: PathT = ".",
        write_to: PathT | None = None,
        write_to_template: str | None = None,
        dist_name: str | None = None,
    ):
        self._relative_to = None if relative_to is None else os.fspath(relative_to)
        self._root = "."
        self.root = os.fspath(root)
        self.write_to = write_to
        self.write_to_template = write_to_template
        self.dist_name = dist_name
        self.parent = None

    @property
    def relative_to(self) -> str | None:
        return self._relative_to

    @property
    def root(self) -> str:
        return self._root

    @classmethod
    def from_file(
        cls, name: str = "pyproject.toml", dist_name: str | None = None, **kwargs: Any
    ) -> Configuration:
        """
        Read Configuration from pyproject.toml (or similar).
        Raises exceptions when file is not found or toml is
        not installed or the file has invalid format or does
        not contain the [tool.setuptools_scm] section.
        """

        with open(name, encoding="UTF-8") as strm:
            data = strm.read()
        defn = _lazy_tomli_load(data)
        try:
            section = defn.get("tool", {})["setuptools_scm"]
        except LookupError as e:
            raise LookupError(
                f"{name} does not contain a tool.setuptools_scm section"
            ) from e
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


def run(self: Command):
    print("RUN->>>>>>>>>>>>>.", type(self))
    super(type(self), self).run()


def _read_dist_name_from_setup_cfg() -> str | None:
    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read(["setup.cfg"])
    return parser.get("metadata", "name", fallback=None)


def finalize_dist(dist: Distribution):
    breakpoint()

    dist_name = dist.metadata.name
    if dist_name is None:
        dist_name = _read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "setuptools_scm":
        return
    try:
        config = Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        return
    else:
        # do something with config

        for cmd in ("sdist", "bdist_wheel"):
            if sdist := dist.get_command_class(cmd):
                dist.cmdclass[cmd] = type(f"npe2_{cmd}", (sdist,), {"run": run})


finalize_dist.order = 100
