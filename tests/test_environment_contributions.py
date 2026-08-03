from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from npe2 import PluginManifest
from npe2._command_registry import CommandRegistry
from npe2.cli import validate
from npe2.manifest.contributions import (
    EnvironmentContribution,
    EnvironmentProvision,
    LocalPackageRequirement,
)


def _worker_manifest(**contributions) -> PluginManifest:
    data = {
        "environments": [
            {
                "id": "example-plugin.worker",
                "display_name": "Worker",
                "python": "3.12.*",
            }
        ],
        "commands": [
            {
                "id": "example-plugin.segment",
                "title": "Segment",
                "python_name": "worker_package.api:segment",
                "environment": "example-plugin.worker",
            }
        ],
    }
    data.update(contributions)
    return PluginManifest(name="example-plugin", contributions=data)


def test_environment_recipe_round_trip(tmp_path: Path) -> None:
    manifest_file = tmp_path / "napari.yaml"
    manifest_file.write_text(
        """
name: example-plugin
contributions:
  environments:
    - id: example-plugin.worker
      display_name: Segmentation worker
      provision: on_install
      python: "3.12.*"
      conda: [numpy=1.26, scikit-image]
      pypi: [segment-anything>=1]
      channels: [conda-forge, pytorch]
      local_packages:
        - path: worker-package
      lockfile: locks/pixi.lock
  commands:
    - id: example-plugin.segment
      title: Segment
      python_name: worker_package.api:segment
      environment: example-plugin.worker
      accepts_worker_context: true
""",
        encoding="utf-8",
    )

    manifest = PluginManifest.from_file(manifest_file)
    [environment] = manifest.contributions.environments or []
    [command] = manifest.contributions.commands or []

    assert environment == EnvironmentContribution(
        id="example-plugin.worker",
        display_name="Segmentation worker",
        provision=EnvironmentProvision.ON_INSTALL,
        python="3.12.*",
        conda=["numpy=1.26", "scikit-image"],
        pypi=["segment-anything>=1"],
        channels=["conda-forge", "pytorch"],
        local_packages=[LocalPackageRequirement(path="worker-package")],
        lockfile="locks/pixi.lock",
    )
    assert command.environment == environment.id
    assert command.accepts_worker_context
    assert (
        PluginManifest(**manifest.model_dump(exclude={"package_metadata"})).model_dump()
        == manifest.model_dump()
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("python", ""),
        ("conda", ["numpy>=1", "NumPy<2"]),
        ("pypi", ["my-package>=1", "my_package<2"]),
        ("channels", []),
        ("channels", ["conda-forge", "conda-forge"]),
        ("lockfile", "/tmp/pixi.lock"),
        ("lockfile", "../pixi.lock"),
        ("lockfile", r"locks\pixi.lock"),
    ],
)
def test_invalid_environment_recipe(field: str, value: object) -> None:
    recipe: dict[str, object] = {
        "id": "example-plugin.worker",
        "display_name": "Worker",
        "python": "3.12",
    }
    recipe[field] = value
    with pytest.raises(ValidationError):
        EnvironmentContribution(**recipe)


def test_environment_provision_defaults_to_on_demand() -> None:
    environment = EnvironmentContribution(
        id="example-plugin.worker",
        display_name="Worker",
        python="3.12",
    )

    assert environment.provision is EnvironmentProvision.ON_DEMAND


@pytest.mark.parametrize("display_name", [None, "", " worker"])
def test_environment_requires_valid_display_name(
    display_name: str | None,
) -> None:
    recipe = {
        "id": "example-plugin.worker",
        "python": "3.12",
    }
    if display_name is not None:
        recipe["display_name"] = display_name

    with pytest.raises(ValidationError, match="display_name"):
        EnvironmentContribution(**recipe)


def test_environment_rejects_invalid_provision_policy() -> None:
    with pytest.raises(ValidationError, match=r"on_install|on_demand"):
        EnvironmentContribution(
            id="example-plugin.worker",
            display_name="Worker",
            provision="eager",
            python="3.12",
        )


@pytest.mark.parametrize("field", ["editable", "extras"])
def test_local_package_contains_only_a_path(field: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        LocalPackageRequirement(path="worker-package", **{field: True})


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "..",
        "../worker",
        "worker/../other",
        "worker//package",
        "/worker",
        r"worker\package",
    ],
)
def test_local_package_path_must_be_manifest_relative(path: str) -> None:
    with pytest.raises(ValidationError, match="safe path relative"):
        LocalPackageRequirement(path=path)


def test_environment_ids_are_unique_and_plugin_qualified() -> None:
    duplicate = [
        {
            "id": "example-plugin.worker",
            "display_name": "First worker",
            "python": "3.12",
        },
        {
            "id": "example-plugin.worker",
            "display_name": "Second worker",
            "python": "3.11",
        },
    ]
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        _worker_manifest(environments=duplicate)

    with pytest.raises(ValidationError, match="current package name"):
        _worker_manifest(
            environments=[
                {
                    "id": "another-plugin.worker",
                    "display_name": "Worker",
                    "python": "3.12",
                }
            ],
            commands=[],
        )


def test_worker_command_requires_target_and_local_environment() -> None:
    with pytest.raises(ValidationError, match="must declare a python_name"):
        _worker_manifest(
            commands=[
                {
                    "id": "example-plugin.segment",
                    "title": "Segment",
                    "environment": "example-plugin.worker",
                }
            ]
        )

    with pytest.raises(ValidationError, match="undeclared environment"):
        _worker_manifest(
            commands=[
                {
                    "id": "example-plugin.segment",
                    "title": "Segment",
                    "python_name": "worker_package.api:segment",
                    "environment": "example-plugin.missing",
                }
            ]
        )

    with pytest.raises(ValidationError, match="owned by plugin"):
        _worker_manifest(
            commands=[
                {
                    "id": "example-plugin.segment",
                    "title": "Segment",
                    "python_name": "worker_package.api:segment",
                    "environment": "another-plugin.worker",
                }
            ]
        )


def test_worker_context_is_only_valid_for_worker_commands() -> None:
    with pytest.raises(ValidationError, match="accepts a worker context"):
        _worker_manifest(
            commands=[
                {
                    "id": "example-plugin.host",
                    "title": "Host command",
                    "python_name": "host_package.api:command",
                    "accepts_worker_context": True,
                }
            ]
        )


@pytest.mark.parametrize(
    ("contribution", "value"),
    [
        (
            "widgets",
            [{"command": "example-plugin.segment", "display_name": "Segment"}],
        ),
        (
            "readers",
            [
                {
                    "command": "example-plugin.segment",
                    "filename_patterns": ["*.tif"],
                }
            ],
        ),
        (
            "writers",
            [{"command": "example-plugin.segment", "layer_types": ["image"]}],
        ),
        (
            "sample_data",
            [
                {
                    "command": "example-plugin.segment",
                    "key": "sample",
                    "display_name": "Sample",
                }
            ],
        ),
    ],
)
def test_worker_commands_cannot_implement_host_contributions(
    contribution: str, value: object
) -> None:
    with pytest.raises(ValidationError, match="cannot implement"):
        _worker_manifest(**{contribution: value})


def test_validate_imports_skips_worker_targets() -> None:
    manifest = _worker_manifest(
        commands=[
            {
                "id": "example-plugin.segment",
                "title": "Segment",
                "python_name": "package_not_installed_in_host.api:segment",
                "environment": "example-plugin.worker",
            }
        ]
    )
    manifest.validate_imports()

    manifest = PluginManifest(
        name="example-plugin",
        contributions={
            "commands": [
                {
                    "id": "example-plugin.host",
                    "title": "Host command",
                    "python_name": "package_not_installed_in_host.api:command",
                }
            ]
        },
    )
    with pytest.raises(ValidationError, match="package_not_installed_in_host"):
        manifest.validate_imports()


def test_validate_cli_skips_worker_target_import(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_file = tmp_path / "napari.yaml"
    manifest_file.write_text(_worker_manifest().yaml(), encoding="utf-8")

    validate(str(manifest_file), imports=True, debug=False)

    assert "valid!" in capsys.readouterr().out


def test_command_registry_does_not_import_worker_target() -> None:
    manifest = _worker_manifest()
    registry = CommandRegistry()

    registry.register_manifest(manifest)

    assert "example-plugin.segment" not in registry


def test_json_schema_contains_environment_contract() -> None:
    schema = PluginManifest.model_json_schema()
    contribution_fields = schema["$defs"]["ContributionPoints"]["properties"]
    command_fields = schema["$defs"]["CommandContribution"]["properties"]
    environment_fields = schema["$defs"]["EnvironmentContribution"]["properties"]
    local_package_fields = schema["$defs"]["LocalPackageRequirement"]["properties"]

    assert schema["properties"]["schema_version"]["default"] == "0.3.0"
    assert "environments" in contribution_fields
    assert environment_fields["provision"]["default"] == "on_demand"
    assert "display_name" in schema["$defs"]["EnvironmentContribution"]["required"]
    assert {"display_name", "provision"} <= environment_fields.keys()
    assert local_package_fields.keys() == {"path"}
    assert "environment" in command_fields
    assert "accepts_worker_context" in command_fields
