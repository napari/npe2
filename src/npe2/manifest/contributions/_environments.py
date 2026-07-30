from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from npe2.manifest import _validators


def _manifest_relative_path(value: str) -> str:
    value = value.strip()
    windows_path = PureWindowsPath(value)
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or "\0" in value
        or path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(
            "must be a safe path relative to the plugin manifest, using '/' separators"
        )
    return value


ManifestRelativePath = Annotated[str, AfterValidator(_manifest_relative_path)]


def _requirement_name(value: str) -> str | None:
    match = re.match(r"([A-Za-z0-9][A-Za-z0-9_.-]*)", value)
    if match is None:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def _reject_duplicate_requirements(values: list[str]) -> list[str]:
    names: set[str] = set()
    for value in values:
        name = _requirement_name(value)
        if name is not None and name in names:
            raise ValueError(f"Duplicate dependency declaration for {name!r}")
        if name is not None:
            names.add(name)
    return values


class LocalPackageRequirement(BaseModel):
    """A Python package shipped alongside the plugin manifest.

    Local packages are installed only in the declared isolated environment. Paths are
    resolved relative to the manifest file by the environment manager.
    """

    path: ManifestRelativePath = Field(
        ...,
        description="Path to the package, relative to the plugin manifest. The package "
        "must be included in the plugin distribution.",
    )

    model_config = ConfigDict(extra="forbid")


class EnvironmentProvision(StrEnum):
    """When napari should provision a managed plugin environment."""

    ON_INSTALL = "on_install"
    ON_DEMAND = "on_demand"


class EnvironmentContribution(BaseModel):
    """Declare a reusable isolated environment for plugin worker commands.

    The host plugin remains installed with napari. Dependencies declared here are
    provisioned separately by napari and are available only to worker commands
    associated with this environment.
    """

    id: Annotated[str, AfterValidator(_validators.environment_id)] = Field(
        ...,
        description="Plugin-qualified identifier for this environment.",
    )
    display_name: Annotated[str, AfterValidator(_validators.display_name)] = Field(
        ...,
        description="User-facing name for this environment.",
    )
    provision: EnvironmentProvision = Field(
        EnvironmentProvision.ON_DEMAND,
        description="When a napari-managed plugin installation should provision this "
        "environment. This does not start worker processes.",
    )
    python: str = Field(
        ...,
        description="Python version constraint for the isolated environment.",
    )
    conda: list[str] = Field(
        default_factory=list,
        description="Conda dependency specifications for the isolated environment.",
    )
    pypi: list[str] = Field(
        default_factory=list,
        description="PEP 508 Python package requirements for the isolated environment.",
    )
    channels: list[str] = Field(
        default_factory=lambda: ["conda-forge"],
        description="Ordered Conda channels used to resolve the environment.",
    )
    local_packages: list[LocalPackageRequirement] = Field(
        default_factory=list,
        description="Python packages shipped alongside the manifest and installed only "
        "in this environment.",
    )
    lockfile: ManifestRelativePath | None = Field(
        None,
        description="Optional lockfile path, relative to the plugin manifest.",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("python")
    @classmethod
    def _validate_python(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Python constraint cannot be empty")
        return value

    @field_validator("conda", "pypi", "channels")
    @classmethod
    def _validate_string_list(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            value = value.strip()
            if not value:
                raise ValueError("Dependency and channel entries cannot be empty")
            if value in result:
                raise ValueError(f"Duplicate entry {value!r}")
            result.append(value)
        return result

    @field_validator("conda", "pypi")
    @classmethod
    def _unique_dependencies(cls, values: list[str]) -> list[str]:
        return _reject_duplicate_requirements(values)

    @field_validator("channels")
    @classmethod
    def _require_channel(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one Conda channel is required")
        return values
