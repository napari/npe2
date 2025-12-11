from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from enum import Enum
from importlib import metadata, util
from logging import getLogger
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

from pydantic import AfterValidator, BeforeValidator, field_validator

from npe2._pydantic_compat import (
    BaseModel,
    Field,
    ModelMetaclass,
    ValidationError,
    _get_inner_type,
    model_validator,
)
from npe2.types import PythonName

from . import _validators
from ._bases import ImportExportModel
from ._package_metadata import PackageMetadata
from .contributions import ContributionPoints
from .utils import Executable, Version

logger = getLogger(__name__)


SCHEMA_VERSION = "0.2.1"
ENTRY_POINT = "napari.manifest"
NPE1_ENTRY_POINT = "napari.plugin"


class Category(str, Enum):
    """Broad plugin categories, values for PluginManifest.categories."""

    # drive devices (webcams, microscopes, etc) to acquire data
    Acquisition = "Acquisition"
    # tools that facilitate labeling, marking, and, erm, "annotating" data within napari
    Annotation = "Annotation"
    # Sample datasets for training, demonstration, learning, etc...
    Dataset = "Dataset"
    # Routines that take in numerical arrays and generally return new arrays or datasets
    # (e.g. scikit image stuff, deconvolution, super-res reconstruction, etc...)
    Image_Processing = "Image Processing"
    # Plugins that read from and/or write to files or data streams
    # not supported natively by napari
    IO = "IO"
    # Plugins that employ machine learning: may facilitate either training or prediction
    # Machine_Learning = "Machine Learning"

    # Tools that extract measurements (i.e. into tabular, graph, or other data formats),
    # such as region properties, etc...
    Measurement = "Measurement"
    # tools that allow registration/alignment between different layers/datasets
    Registration = "Registration"
    # tools that identify objects and/or boundaries in datasets
    # (including, but not limited to, images)
    Segmentation = "Segmentation"
    # tools that simulate some physical process.
    # microscope/PSF generators, optics simulators, astronomy simulations, etc...
    Simulation = "Simulation"
    # plugins that modify the look and feel of napari
    Themes = "Themes"
    # linear and or nonlinear registrations, general data transformations and mappings
    Transformations = "Transformations"
    # Conveniences, widgets, etc... stuff that could conceivably be "core"
    # but which is community-supported
    Utilities = "Utilities"
    # tools for plotting, rendering, and visualization
    # (on top of those provided by napari)
    Visualization = "Visualization"

    def __str__(self) -> str:
        return self.value  # pragma: no cover


class DiscoverResults(NamedTuple):
    manifest: PluginManifest | None
    distribution: metadata.Distribution | None
    error: Exception | None


class PluginManifest(ImportExportModel):
    class Config:
        extra = "ignore"
        validate_assignment = True

    # VS Code uses <publisher>.<name> as a unique ID for the extension
    # should this just be the package name ... not the module name? (yes)
    # do we normalize this? (i.e. underscores / dashes ?) (no)
    # TODO: enforce that this matches the package name

    name: Annotated[str, BeforeValidator(_validators.package_name)] = Field(
        ...,
        description="The name of the plugin. Though this field is mandatory, it *must*"
        " match the package `name` as defined in the python package metadata.",
        allow_mutation=False,
    )

    display_name: Annotated[str, AfterValidator(_validators.display_name)] = Field(
        "",
        description="User-facing text to display as the name of this plugin. "
        "Must be 3-90 characters long and must not begin or end with an underscore, "
        "white space, or non-word character. If not provided, the manifest `name` "
        "will be used as the display name.",
        min_length=3,
        max_length=90,
    )

    visibility: Literal["public", "hidden"] = Field(
        "public",
        description="Whether this plugin should be searchable and visible in "
        "the built-in plugin installer and the napari hub. By default (`'public'`) "
        "all plugins are visible. To prevent your plugin from appearing in search "
        "results, change this to `'hidden'`.",
    )

    icon: Annotated[str, AfterValidator(_validators.icon_path)] = Field(
        "",
        description="The path to a square PNG icon of at least 128x128 pixels (256x256 "
        "for Retina screens). May be one of: "
        "<ul><li>a secure (https) URL </li>"
        "<li>a path relative to the manifest file, (must be shipped in the sdist)</li>"
        "<li>a string in the format `{package}:{resource}`, where `package` and "
        "`resource` are arguments to `importlib.resources.path(package, resource)`, "
        "(e.g. `top_module.some_folder:my_logo.png`).</li></ul>",
    )

    categories: list[Category] = Field(
        default_factory=list,
        description="A list of categories that this plugin belongs to. This is used to "
        f"help users discover your plugin. Allowed values: `[{', '.join(Category)}]`",
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
        json_schema_extra={"always_export": True},
    )

    # TODO:
    # Perhaps we should version the plugin interface (not so the manifest, but
    # the actual mechanism/consumption of plugin information) independently
    # of napari itself

    on_activate: (
        Annotated[PythonName, AfterValidator(_validators.python_name)] | None
    ) = Field(
        default=None,
        description="Fully qualified python path to a function that will be called "
        "upon plugin activation (e.g. `'my_plugin.some_module:activate'`). The "
        "activate function can be used to connect command ids to python callables, or"
        " perform other side-effects. A plugin will be 'activated' when one of its "
        "contributions is requested by the user (such as a widget, or reader).",
    )

    on_deactivate: (
        Annotated[PythonName, AfterValidator(_validators.python_name)] | None
    ) = Field(
        default=None,
        description="Fully qualified python path to a function that will be called "
        "when a user deactivates a plugin (e.g. `'my_plugin.some_module:deactivate'`)"
        ". This is optional, and may be used to perform any plugin cleanup.",
    )

    contributions: ContributionPoints = Field(
        default_factory=ContributionPoints,
        description="An object describing the plugin's "
        "[contributions](./contributions)",
    )

    package_metadata: PackageMetadata | None = Field(
        None,
        description="Package metadata following "
        "https://packaging.python.org/specifications/core-metadata/. "
        "For normal (non-dynamic) plugins, this data will come from the package's "
        "setup.cfg",
        hide_docs=True,
    )

    npe1_shim: bool = Field(
        False,
        description="Whether this manifest was created as a shim for an npe1 plugin.",
        hide_docs=True,
    )

    def __init__(self, **data):
        super().__init__(**data)
        if self.package_metadata is None and self.name:
            with suppress(metadata.PackageNotFoundError):
                meta = metadata.distribution(self.name).metadata
                self.package_metadata = PackageMetadata.from_dist_metadata(meta)

        if not self.npe1_shim:
            # assign plugin name on all contributions that have a private
            # _plugin_name field.
            for _, value in self.contributions or ():
                for item in value if isinstance(value, list) else [value]:
                    if isinstance(item, Executable):
                        item._plugin_name = self.name

    def __hash__(self):
        return hash((self.name, self.package_version))

    @property
    def license(self) -> str | None:
        return self.package_metadata.license if self.package_metadata else None

    @property
    def package_version(self) -> str | None:
        return self.package_metadata.version if self.package_metadata else None

    @property
    def description(self) -> str | None:
        return self.package_metadata.summary if self.package_metadata else None

    @property
    def author(self) -> str | None:
        return self.package_metadata.author if self.package_metadata else None

    @property
    def is_visible(self) -> bool:
        return self.visibility == "public"

    @field_validator("contributions", mode="before")
    def _coerce_none_contributions(cls, value):
        return ContributionPoints() if value is None else value

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, values: dict) -> dict:
        mf_name = _validators.package_name(values["name"])

        # validate schema version
        declared_version = Version.parse(
            values.get("schema_version", cls.model_fields["schema_version"].default)
        )
        current_version = Version.parse(SCHEMA_VERSION)
        if current_version < declared_version:
            import warnings

            warnings.warn(
                f"The declared schema version for plugin {mf_name!r} "
                f"({declared_version}) is newer than npe2's schema version "
                f"({current_version}). Things may break, you should upgrade npe2.",
                stacklevel=2,
            )

        invalid_commands: list[str] = []
        if values.get("contributions") is not None:
            contributions = values["contributions"]
            if isinstance(contributions, dict):
                contributions = ContributionPoints(**contributions)
            invalid_commands.extend(
                command.id
                for command in contributions.commands or []
                if not command.id.startswith(f"{mf_name}.")
            )

        if invalid_commands:
            raise ValueError(
                "Commands identifiers must start with the current package name "
                f"followed by a dot: '{mf_name}'. The following commands do not: "
                f"{invalid_commands}"
            )

        if not values.get("display_name"):
            values["display_name"] = mf_name

        return values

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
        dist = metadata.distribution(name)  # may raise PackageNotFoundError
        pm = _from_dist(dist)
        if not pm:
            raise ValueError(
                "Distribution {name!r} exists but does not provide a napari manifest"
            )
        return pm

    @classmethod
    def discover(cls, paths: Sequence[str | Path] = ()) -> Iterator[DiscoverResults]:
        """Discover manifests in the environment.

        This function searches for installed python packages with a matching
        entry point group and then attempts to resolve the manifest file.

        The manifest file should be specified in the plugin's ``setup.cfg`` or
        ``setup.py`` file using the [entry point group][1]: "napari.manifest".
        For example, this would be the section for a plugin "npe-tester" with
        "napari.yaml" as the manifest file:

        .. code-block:: cfg

            [options.entry_points]
            napari.manifest =
                npe2-tester = npe2_tester:napari.yaml

        The manifest file is specified relative to the submodule root path.
        So for the example it will be loaded from:
        ``<path/to/npe2-tester>/napari.yaml``.

        [1]: https://packaging.python.org/specifications/entry-points/

        Parameters
        ----------
        paths : Sequence[str], optional
            paths to add to sys.path while discovering.

        Yields
        ------
        DiscoverResults: (3 namedtuples: manifest, entrypoint, error)
            3-tuples with either manifest or (entrypoint and error) being None.
        """
        with _temporary_path_additions(paths):
            for dist in metadata.distributions():
                try:
                    pm = _from_dist(dist)
                    if pm:
                        yield DiscoverResults(pm, dist, None)
                except ValidationError as e:
                    logger.warning(
                        "Invalid schema for package %r, please run"
                        " 'npe2 validate %s' to check for manifest errors.",
                        dist.metadata["Name"],
                        dist.metadata["Name"],
                    )
                    yield DiscoverResults(None, dist, e)

                except Exception as e:
                    logger.error(
                        "{} -> {!r} could not be imported: {}".format(
                            ENTRY_POINT, dist.metadata["Name"], e
                        )
                    )
                    yield DiscoverResults(None, dist, e)

    @classmethod
    def _from_entrypoint(
        cls,
        entry_point: metadata.EntryPoint,
        distribution: metadata.Distribution | None = None,
    ) -> PluginManifest:
        module_match = entry_point.pattern.match(entry_point.value)
        assert module_match is not None
        module = module_match.group("module")

        spec = util.find_spec(module or "")
        if not spec:  # pragma: no cover
            raise ValueError(
                f"Cannot find module {module!r} declared in "
                f"entrypoint: {entry_point.value!r}"
            )

        file_match = entry_point.pattern.match(entry_point.value)
        assert file_match is not None
        fname = file_match.group("attr")

        for loc in spec.submodule_search_locations or []:
            mf_file = Path(loc) / fname
            if mf_file.exists():
                mf = PluginManifest.from_file(mf_file)
                if distribution is not None:
                    meta = PackageMetadata.from_dist_metadata(distribution.metadata)
                    mf.package_metadata = meta

                    if mf.name != meta.name:
                        raise ValueError(  # pragma: no cover
                            f"The name field in the manifest ({mf.name!r}) "
                            f"must match the package name ({meta.name!r})"
                        )
                    return mf

        raise FileNotFoundError(  # pragma: no cover
            f"Could not find file {fname!r} in module {module!r}"
        )

    @classmethod
    def _from_package_or_name(cls, package_or_filename: Path | str) -> PluginManifest:
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
        from npe2 import PluginManifest
        from npe2._pydantic_compat import ValidationError

        try:
            return PluginManifest.from_file(package_or_filename)
        except ValidationError:  # pragma: no cover
            raise
        except (FileNotFoundError, ValueError):
            try:
                return PluginManifest.from_distribution(str(package_or_filename))
            except ValidationError:  # pragma: no cover
                raise
            except Exception as e:
                raise ValueError(
                    f"Could not find manifest for {package_or_filename!r} as either a "
                    "package name or a file.."
                ) from e

    def _serialized_data(self, **kwargs):
        kwargs.setdefault("exclude", {"package_metadata"})
        return super()._serialized_data(**kwargs)

    def validate_imports(self) -> None:
        """Checks recursively that all `python_name` fields are actually importable."""
        from .utils import import_python_name

        errors = []

        def check_pynames(m: BaseModel, loc=()):
            for name, value in m:
                if not value:
                    continue
                if isinstance(value, BaseModel):
                    return check_pynames(value, (*loc, name))
                annotation = type(m).model_fields[name].annotation
                if isinstance(value, list) and isinstance(
                    _get_inner_type(annotation), ModelMetaclass
                ):
                    return [check_pynames(i, (*loc, n)) for n, i in enumerate(value)]
                if _get_inner_type(annotation) is PythonName:
                    try:
                        import_python_name(value)
                    except (ImportError, AttributeError) as e:
                        errors.append(
                            {
                                "type": "value_error",
                                "loc": (*loc, name),
                                "input": value,
                                "ctx": {"error": e},
                            }
                        )

        check_pynames(self)
        if errors:
            raise ValidationError.from_exception_data(
                "Some python names are invalid", line_errors=errors
            )

    def json(self, **kwargs):
        # for backward compatibility
        return self.model_dump_json(**kwargs)


def _noop(*_, **__):
    return []  # pragma: no cover


@contextmanager
def discovery_blocked():
    orig = PluginManifest.discover
    PluginManifest.discover = _noop  # type: ignore [method-assign]
    try:
        yield
    finally:
        PluginManifest.discover = orig  # type: ignore [method-assign]


@contextmanager
def _temporary_path_additions(paths: Sequence[str | Path] = ()):
    if paths and (not isinstance(paths, Sequence) or isinstance(paths, str)):
        raise TypeError("paths must be a sequence of strings")  # pragma: no cover
    for p in reversed(paths):
        sys.path.insert(0, str(p))
    try:
        yield
    finally:
        for p in paths:
            sys.path.remove(str(p))


def _from_dist(dist: metadata.Distribution) -> PluginManifest | None:
    """Return PluginManifest or NPE1Adapter for a metadata.Distribution object.

    ...depending on which entry points are available.
    """
    _npe1, _npe2 = [], None
    for ep in dist.entry_points:
        if ep.group == NPE1_ENTRY_POINT:
            _npe1.append(ep)
        elif ep.group == ENTRY_POINT:
            _npe2 = ep
    if _npe2:
        return PluginManifest._from_entrypoint(_npe2, dist)
    elif _npe1:
        from ._npe1_adapter import NPE1Adapter

        return NPE1Adapter(dist=dist)
    return None


if __name__ == "__main__":
    import json

    dkt = PluginManifest.model_json_schema()
    print(json.dumps(dkt, indent=2))
