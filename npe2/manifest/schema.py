from __future__ import annotations

import json
import re
import sys
from contextlib import contextmanager
from enum import Enum
from importlib import util
from logging import getLogger
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterator,
    NamedTuple,
    Optional,
    Sequence,
    Union,
)

import pytomlpp as toml
import yaml
from pydantic import BaseModel, Extra, Field, ValidationError, root_validator, validator

from . import _validators
from .contributions import ContributionPoints
from .package_metadata import PackageMetadata
from .utils import Version

try:
    from importlib.metadata import Distribution, distributions
except ImportError:
    from importlib_metadata import Distribution, distributions  # type: ignore

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint

spdx_ids = (Path(__file__).parent / "spdx.txt").read_text().splitlines()
SPDX = Enum("SPDX", {i.replace("-", "_"): i for i in spdx_ids})  # type: ignore

logger = getLogger(__name__)


SCHEMA_VERSION = "0.1.0"
ENTRY_POINT = "napari.manifest"
_display_name_pattern = re.compile(r"^[^\W_][\w -~]{1,38}[^\W_]$")


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

    display_name: str = Field(
        "",
        description="User-facing text to display as the name of this plugin",
        # Must be 3-40 characters long, containing printable word characters,
        # and must not begin or end with an underscore, white space, or
        # non-word character.
    )

    # Plugins rely on certain guarantees to interoperate propertly with the
    # plugin engine. These include the manifest specification, conventions
    # around python packaging, command api's, etc. Together these form a
    # "contract". The version of this contract is the "schema version."
    #
    # The first release of npe2 defines the first schema version.
    # As the contract around plugins evolve the SCHEMA_VERSION should be
    # increased follow SemVer rules. Note that sometimes the version number
    # will change even though no npe2 code changes.
    #
    # The `schema_version` field declares the version of the contract that this
    # plugin targets.
    schema_version: str = Field(
        SCHEMA_VERSION,
        description="A SemVer compatible version string matching the napari plugin "
        "schema version that the plugin is compatible with.",
    )

    # TODO:
    # Perhaps we should version the plugin interface (not so the manifest, but
    # the actual mechanism/consumption of plugin information) independently
    # of napari itself

    on_activate: Optional[str] = Field(
        default=None,
        description="Fully qualified python path to a function that will be called "
        "upon plugin activation (e.g. my_plugin._some_module:activate). The activate "
        "function can be used to connect command ids to python callables, or perform "
        "other side-effects. A plugin will be 'activated' when one of its "
        "contributions is requested by the user (such as a widget, or reader).",
    )
    _validate_activate_func = validator("on_activate", allow_reuse=True)(
        _validators.python_name
    )
    on_deactivate: Optional[str] = Field(
        default=None,
        description="Fully qualified python path to a function that will be called "
        "when a user deactivates a plugin (e.g. my_plugin._some_module:deactivate). "
        "This is optional, but may be used to perform any plugin cleanup.",
    )
    _validate_deactivate_func = validator("on_deactivate", allow_reuse=True)(
        _validators.python_name
    )

    contributions: Optional[ContributionPoints]

    _manifest_file: Optional[Path] = None
    package_metadata: Optional[PackageMetadata] = None

    @property
    def license(self) -> Optional[str]:
        return self.package_metadata.license if self.package_metadata else None

    @property
    def version(self) -> Optional[str]:
        return self.package_metadata.version if self.package_metadata else None

    @property
    def description(self) -> Optional[str]:
        return self.package_metadata.summary if self.package_metadata else None

    @property
    def author(self) -> Optional[str]:
        return self.package_metadata.author if self.package_metadata else None

    @validator("display_name")
    def validate_display_name(cls, v):
        if not _display_name_pattern.match(v):
            raise ValueError(
                f"{v} is not a valid display_name.  The display_name must "
                "be 3-40 characters long, containing printable word characters, "
                "and must not begin or end with an underscore, white space, or "
                "non-word character."
            )
        return v

    @root_validator
    def _validate_root(cls, values: dict) -> dict:
        # validate schema version
        declared_version = Version.parse(values.get("schema_version", ""))
        current_version = Version.parse(SCHEMA_VERSION)
        if current_version < declared_version:
            raise ValueError(
                dedent(
                    f"The declared schema version {declared_version} is "
                    f"newer than npe2's schema version: {current_version}. You may "
                    "need to upgrade npe2."
                )
            )

        invalid_commands = []
        if values.get("contributions") is not None:
            for command in values["contributions"].commands or []:
                id_start_actual = command.id.split(".")[0]
                if values["name"] != id_start_actual:
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
        with _schema_version_in_fields_set(self):
            d = json.loads(self.json(exclude_unset=True))
            if pyproject:
                d = {"tool": {"napari": d}}
            return toml.dumps(d)

    def yaml(self) -> str:
        with _schema_version_in_fields_set(self):
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
                return PluginManifest._from_entrypoint(ep, dist)
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

    @classmethod
    def discover(
        cls,
        entry_point_group: str = ENTRY_POINT,
        paths: Sequence[Union[str, Path]] = (),
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
        with _temporary_path_additions(paths):
            for dist in distributions():
                for ep in dist.entry_points:
                    if ep.group != entry_point_group:
                        continue
                    try:
                        pm = cls._from_entrypoint(ep, dist)
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
    def _from_entrypoint(
        cls, entry_point: EntryPoint, distribution: Optional[Distribution] = None
    ) -> PluginManifest:

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
            mf_file = Path(loc) / fname
            if mf_file.exists():
                mf = PluginManifest.from_file(mf_file)
                if distribution is not None:
                    meta = PackageMetadata.from_dist_metadata(distribution.metadata)
                    mf.package_metadata = meta

                    assert mf.name == meta.name, "Manifest name must match package name"
                    return mf

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
def _temporary_path_additions(paths: Sequence[Union[str, Path]] = ()):
    for p in reversed(paths):
        sys.path.insert(0, str(p))
    try:
        yield
    finally:
        for p in paths:
            sys.path.remove(str(p))


@contextmanager
def _schema_version_in_fields_set(manifest: PluginManifest):
    was_there = "schema_version" in manifest.__fields_set__
    manifest.__fields_set__.add("schema_version")
    try:
        yield
    finally:
        if not was_there:
            manifest.__fields_set__.discard("schema_version")


if __name__ == "__main__":
    print(PluginManifest.schema_json())
