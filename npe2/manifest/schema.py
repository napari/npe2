from __future__ import annotations

import types
from enum import Enum
from importlib import import_module, util
from logging import getLogger
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, root_validator

from .contributions import ContributionPoints

if TYPE_CHECKING:
    from email.message import Message
    from importlib.metadata import EntryPoint


spdx_ids = (Path(__file__).parent / "spdx.txt").read_text().splitlines()
SPDX = Enum("SPDX", {i.replace("-", "_"): i for i in spdx_ids})  # type: ignore

logger = getLogger(__name__)

ENTRY_POINT = "napari.manifest"


class PluginManifest(BaseModel):
    # VS Code uses <publisher>.<name> as a unique ID for the extension
    # should this just be the package name ... not the module name? (probably yes)
    # do we normalize this? (i.e. underscores / dashes ?)
    # TODO: enforce that this matches the package name
    name: str = Field(
        ...,
        description="The name of the plugin - should be all lowercase with no spaces.",
    )
    # this is not something that has an equivalent on PyPI ...
    # it might be a good field with which we can identify trusted source
    # but... it's not entire clear how that "trust" gets validated at the moment
    publisher: Optional[str] = Field(
        None,
        description="The publisher name - can be an individual or an organization",
    )
    # easy one... we need this.  character limit?  256 char?
    display_name: str = Field(
        "",
        description="The display name for the extension used in the Marketplace.",
    )
    # take this from setup.cfg
    description: Optional[str] = Field(
        description="A short description of what your extension is and does."
    )

    # TODO:
    # Perhaps we should version the plugin interface (not so the manifest, but
    # the actual mechanism/consumption of plugin information) independently
    # of napari itself

    # mechanistic things:
    # this is the module that has the activate() function
    entry_point: str = Field(
        ...,
        description="The extension entry point. This should be a fully qualified "
        "module string. e.g. `foo.bar.baz`",
    )

    # this comes from setup.cfg
    version: Optional[str] = Field(None, description="SemVer compatible version.")
    # this should come from setup.cfg ... but they don't requireq SPDX
    license: Optional[SPDX] = None

    contributions: Optional[ContributionPoints]
    # # this would be there only for the hub.  which is not immediately planning
    # # to support open ended keywords
    # keywords: List[str] = Field(
    #     default_factory=list,
    #     description="An array of keywords to make it easier to find the "
    #     "extension. These are included with other extension Tags on the "
    #     "Marketplace. This list is currently limited to 5 keywords",
    # )
    # the hub *is* planning on supporting categories
    categories: List[str] = Field(
        default_factory=list,
        description="specifically defined classifiers",
    )
    # in the absense of input. should be inferred from version (require using rc ...)
    # or use `classifiers = Status`
    preview: Optional[bool] = Field(
        None,
        description="Sets the extension to be flagged as a Preview in napari-hub.",
    )
    private: bool = Field(False, description="Whether this extension is private")

    # activationEvents: Optional[List[ActivationEvent]] = Field(
    #     default_factory=list,
    #     description="Events upon which your extension becomes active.",
    # )

    # @validator("activationEvents", pre=True)
    # def _validateActivationEvent(cls, val):
    #     return [
    #         dict(zip(("kind", "id"), x.split(":"))) if ":" in x else x
    #         for x in val
    #     ]

    _manifest_file: Optional[Path] = None

    @root_validator
    def _validate_root(cls, values):
        invalid_commands = []
        if "contributions" in values:
            for command in values["contributions"].commands:
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

    def toml(self):
        import toml

        return toml.dumps({"tool": {"napari": self.dict(exclude_unset=True)}})

    def yaml(self):
        import json

        import yaml

        return yaml.safe_dump(json.loads(self.json(exclude_unset=True)))

    @property
    def key(self):
        return f"{self.publisher}.{self.name}"

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

        if path.suffix.lower() == ".json":
            loader = import_module("json").load  # type: ignore
        elif path.suffix.lower() == ".toml":
            loader = import_module("toml").load  # type: ignore
        elif path.suffix.lower() in (".yaml", ".yml"):
            loader = import_module("yaml").safe_load  # type: ignore
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

    # should these be on this model itself? or helper functions elsewhere

    def import_entry_point(self) -> types.ModuleType:
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
        if self.preview is None:
            for k, v in getattr(metadata, "_headers"):
                if k.lower() == "classifier" and v.lower().startswith(
                    "development status"
                ):
                    self.preview = int(v.split(":: ")[-1][0]) < 3
                    break

    @classmethod
    def discover(cls, entry_point_group=ENTRY_POINT) -> Iterator[PluginManifest]:
        """Discover manifests in the environment.

        This function searches for installed python packages with a matching
        entry point group and then attempts to resolve the manifest file.

        The manifest file should be specified in the plugin's `setup.cfg` file
        using the [entry point group][1]: "napari.manifest". For example, this
        would be the section for a plugin "npe-tester" with "napari.yaml" as the
        manifest file:

        ```cfg
        [options.entry_points]
        napari.manifest =
            npe2-tester = npe2_tester:napari.yaml
        ```

        The manifest file is specified relative to the submodule root path.
        So for the example it will be loaded from:
        `<path/to/npe2-tester>/napari.yaml`.

        [1]: https://packaging.python.org/specifications/entry-points/
        """
        try:
            from importlib.metadata import distributions
        except ImportError:
            from importlib_metadata import distributions  # type: ignore

        logger.debug("Discovering npe2 plugin manifests.")
        for dist in distributions():
            for ep in dist.entry_points:
                if ep.group != entry_point_group:
                    continue
                try:
                    pm = cls._from_entrypoint(ep)
                    pm._populate_missing_meta(dist.metadata)
                    yield pm
                except ValidationError:
                    logger.warning(msg=f"Invalid schema {ep.value!r}")
                except Exception as e:
                    logger.warning(
                        "%s -> %r could not be imported: %s"
                        % (entry_point_group, ep.value, e)
                    )

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
            except Exception:
                raise ValueError(
                    f"Could not find manifest for {package_or_filename!r} as either a "
                    "package name or a file.."
                )

    ValidationError = ValidationError  # for convenience of access


if __name__ == "__main__":
    print(PluginManifest.schema_json())
