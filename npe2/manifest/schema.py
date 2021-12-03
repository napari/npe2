from __future__ import annotations

import json
import sys
import types
from contextlib import contextmanager
from enum import Enum
from importlib import import_module, util
from logging import getLogger
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    NamedTuple,
    Optional,
    Sequence,
    Union,
)

import pytomlpp as toml
import yaml
from pydantic import BaseModel, Extra, Field, ValidationError, root_validator

from .contributions import ContributionPoints

try:
    from importlib.metadata import distributions
except ImportError:
    from importlib_metadata import distributions  # type: ignore

if TYPE_CHECKING:
    from email.message import Message
    from importlib.metadata import EntryPoint

spdx_ids = (Path(__file__).parent / "spdx.txt").read_text().splitlines()
SPDX = Enum("SPDX", {i.replace("-", "_"): i for i in spdx_ids})  # type: ignore

logger = getLogger(__name__)

ENTRY_POINT = "napari.manifest"


class DiscoverResults(NamedTuple):
    manifest: Optional[PluginManifest]
    entrypoint: Optional[EntryPoint]
    error: Optional[Exception]


class PluginManifest(BaseModel):

    # VS Code uses <publisher>.<name> as a unique ID for the extension
    # should this just be the package name ... not the module name? (yes)
    # do we normalize this? (i.e. underscores / dashes ?) (no)
    # TODO: enforce that this matches the package name

    name: str = Field(
        ...,
        description="The name of the plugin. Should correspond to the python "
        "package name for this plugin.",
    )

    author: Optional[str] = Field(
        None,
        description="The author name(s). When unspecified, the description is "
        "take from the 'Author' field of the package metadata.",
    )

    display_name: str = Field(
        "",
        description="User-facing text to display as the name of this plugin",
        # Must be 3-40 characters long, containing printable word characters,
        # and must not begin or end with an underscore, white space, or
        # non-word character.
        regex=r"^[^\W_][\w -~]{1,38}[^\W_]$",
    )

    description: Optional[str] = Field(
        description="A short description of what your extension is and does."
        "When unspecified, the description is taken from package metadata."
    )

    # TODO:
    # Perhaps we should version the plugin interface (not so the manifest, but
    # the actual mechanism/consumption of plugin information) independently
    # of napari itself

    # The module that has the activate() function
    entry_point: Optional[str] = Field(
        default=None,
        description="The extension entry point. This should be a fully "
        "qualified module string. e.g. `foo.bar.baz` for a module containing "
        "the plugin's activate() function.",
    )

    # this should come from setup.cfg ... but they don't require SPDX
    license: Optional[SPDX] = None

    version: Optional[str] = Field(
        None,
        description="SemVer compatible version. When unspecified the version "
        "is taken from package metadata.",
    )

    contributions: Optional[ContributionPoints]

    _manifest_file: Optional[Path] = None

    @root_validator
    def _validate_root(cls, values: dict) -> dict:
        invalid_commands = []
        if values.get("contributions") is not None:
            for command in values["contributions"].commands or []:
                if not command.id.startswith(values["name"]):
                    invalid_commands.append(command.id)

        if invalid_commands:
            raise ValueError(
                dedent(
                    f"""Commands identifiers must start with the current package name {values['name']!r}
            the following commands where found to break this assumption:
                {invalid_commands}
            """
                )
            )

        return values

    def toml(self, pyproject=False) -> str:
        d = json.loads(self.json(exclude_unset=True))
        if pyproject:
            d = {"tool": {"napari": d}}
        return toml.dumps(d)

    def yaml(self) -> str:
        return yaml.safe_dump(json.loads(self.json(exclude_unset=True)))

    @classmethod
    def from_distribution(cls, name: str) -> PluginManifest:
        """Return PluginManifest given a distribution (package) name.

        Parameters
        ----------
        name : str
            Name of a python distribution installed in the environment.
            Note: this is the package name, not the top level module name,
            (e.g. "scikit-image", not "skimage").

        Returns
        -------
        PluginManifest
            The parsed manifest.

        Raises
        ------
        ValueError
            If the distribution exists, but does not provide a manifest
        PackageNotFoundError
            If there is no distribution found for `name`
        ValidationError
            If the manifest is not valid
        """
        from importlib.metadata import distribution

        dist = distribution(name)  # may raise PackageNotFoundError
        for ep in dist.entry_points:
            if ep.group == ENTRY_POINT:
                pm = PluginManifest._from_entrypoint(ep)
                pm._populate_missing_meta(dist.metadata)
                return pm
        raise ValueError(
            "Distribution {name!r} exists but does not provide a napari manifest"
        )

    @classmethod
    def from_file(cls, path: Union[Path, str]) -> PluginManifest:
        """Parse PluginManifest from a specific file.

        Parameters
        ----------
        path : Path or str
            Path to a manifest.  Must have extension {'.json', '.yaml', '.yml', '.toml'}

        Returns
        -------
        PluginManifest
            The parsed manifest.

        Raises
        ------
        FileNotFoundError
            If `path` does not exist.
        ValueError
            If the file extension is not in {'.json', '.yaml', '.yml', '.toml'}
        """
        path = Path(path).expanduser().absolute().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        loader: Callable
        if path.suffix.lower() == ".json":
            loader = json.load
        elif path.suffix.lower() == ".toml":
            loader = toml.load
        elif path.suffix.lower() in (".yaml", ".yml"):
            loader = yaml.safe_load
        else:
            raise ValueError(f"unrecognized file extension: {path}")

        with open(path) as f:
            data = loader(f) or {}

        if path.name == "pyproject.toml":
            data = data["tool"]["napari"]

        mf = cls(**data)
        mf._manifest_file = path
        return mf

    class Config:
        use_enum_values = True  # only needed for SPDX
        underscore_attrs_are_private = True
        extra = Extra.forbid

    # should these be on this model itself? or helper functions elsewhere

    def import_entry_point(self) -> types.ModuleType:
        if not self.entry_point:
            raise ModuleNotFoundError(f"Plugin {self.name} declares no entry_point")
        return import_module(self.entry_point)

    def activate(self, context=None) -> Any:
        # TODO: work on context object
        try:
            mod = self.import_entry_point()
        except ModuleNotFoundError:
            # currently, we're playing with the idea that a command could register
            # itself with a qualified python name.  In some cases, this obviates the
            # need for the activate function... so it should be acceptable to omit it.
            return None

        if callable(getattr(mod, "activate", None)):
            return mod.activate(context)  # type: ignore

    def deactivate(self, context=None):
        mod = self.import_entry_point()
        if callable(getattr(mod, "deactivate", None)):
            return mod.deactivate(context)  # type: ignore

    def _populate_missing_meta(self, metadata: Message):
        """add missing items from an importlib metadata object"""
        if not self.name:
            self.name = metadata["Name"]
        if not self.version:
            self.version = metadata["Version"]
        if not self.description:
            self.description = metadata["Summary"]
        if not self.license:
            self.license = metadata["License"]

    @classmethod
    def discover(
        cls, entry_point_group: str = ENTRY_POINT, paths: Sequence[str] = ()
    ) -> Iterator[DiscoverResults]:
        """Discover manifests in the environment.

        This function searches for installed python packages with a matching
        entry point group and then attempts to resolve the manifest file.

        The manifest file should be specified in the plugin's `setup.cfg` or
        `setup.py` file using the [entry point group][1]: "napari.manifest".
        For example, this would be the section for a plugin "npe-tester" with
        "napari.yaml" as the manifest file:

        ```cfg
        [options.entry_points]
        napari.manifest =
            npe2-tester = npe2_tester:napari.yaml
        ```

        The manifest file is specified relative to the submodule root path.
        So for the example it will be loaded from:
        `<path/to/npe2-tester>/napari.yaml`.

        [1]: https://packaging.python.org/specifications/entry-points/

        Parameters
        ----------
        entry_point_group : str, optional
            name of entry point group to discover, by default 'napari.manifest'
        paths : Sequence[str], optional
            paths to add to sys.path while discovering.

        Yields
        ------
        DiscoverResults: (3 namedtuples: manifest, entrypoint, error)
            3-tuples with either manifest or (entrypoint and error) being None.
        """
        with temporary_path_additions(paths):
            for dist in distributions():
                for ep in dist.entry_points:
                    if ep.group != entry_point_group:
                        continue
                    try:
                        pm = cls._from_entrypoint(ep)
                        pm._populate_missing_meta(dist.metadata)
                        yield DiscoverResults(pm, ep, None)
                    except ValidationError as e:
                        logger.warning(msg=f"Invalid schema {ep.value!r}")
                        yield DiscoverResults(None, ep, e)
                    except Exception as e:
                        logger.error(
                            "%s -> %r could not be imported: %s"
                            % (entry_point_group, ep.value, e)
                        )
                        yield DiscoverResults(None, ep, e)

    @classmethod
    def _from_entrypoint(cls, entry_point: EntryPoint) -> PluginManifest:

        match = entry_point.pattern.match(entry_point.value)  # type: ignore
        module = match.group("module")

        spec = util.find_spec(module or "")
        if not spec:
            raise ValueError(
                f"Cannot find module {module!r} declared in "
                f"entrypoint: {entry_point.value!r}"
            )

        match = entry_point.pattern.match(entry_point.value)  # type: ignore
        fname = match.group("attr")

        for loc in spec.submodule_search_locations or []:
            mf = Path(loc) / fname
            if mf.exists():
                return PluginManifest.from_file(mf)
        raise FileNotFoundError(f"Could not find file {fname!r} in module {module!r}")

    @classmethod
    def _from_package_or_name(
        cls, package_or_filename: Union[Path, str]
    ) -> PluginManifest:
        """Internal convenience function, calls both `from_file` and `from_distribution`

        Parameters
        ----------
        package_or_filename : Union[Path, str]
            Either a filename or a package name.  Will be tried first as a filename, and
            then as a distribution name.

        Returns
        -------
        PluginManifest
            [description]

        Raises
        ------
        ValidationError
            If the name can be resolved as either a distribution name or a file,
            but the manifest is not valid.
        ValueError
            If the name does not resolve to either a distribution name or a filename.

        """
        from pydantic import ValidationError

        from npe2 import PluginManifest

        try:
            return PluginManifest.from_file(package_or_filename)
        except ValidationError:
            raise
        except (FileNotFoundError, ValueError):
            try:
                return PluginManifest.from_distribution(str(package_or_filename))
            except ValidationError:
                raise
            except Exception as e:
                raise ValueError(
                    f"Could not find manifest for {package_or_filename!r} as either a "
                    "package name or a file.."
                ) from e

    ValidationError = ValidationError  # for convenience of access


@contextmanager
def temporary_path_additions(paths: Sequence[str] = ()):
    for p in reversed(paths):
        sys.path.insert(0, p)
    try:
        yield
    finally:
        for p in paths:
            sys.path.remove(p)


if __name__ == "__main__":
    print(PluginManifest.schema_json())
