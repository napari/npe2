import json
import sys

import pytest
from pydantic import ValidationError

from npe2 import PluginManifest
from npe2.cli import main


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path
    manifests_and_errors = list(PluginManifest.discover())
    assert len(manifests_and_errors) == 0


def test_discover(uses_sample_plugin):
    discover_results = list(PluginManifest.discover())
    assert len(discover_results) == 1
    [(manifest, entrypoint, error)] = discover_results
    assert manifest and manifest.name == "my_plugin"
    assert entrypoint and entrypoint.group == "napari.manifest"
    assert entrypoint.value == "my_plugin:napari.yaml"
    assert error is None


def test_cli(monkeypatch, sample_path):
    cmd = ["npe2", "validate", str(sample_path / "my_plugin" / "napari.yaml")]
    monkeypatch.setattr(sys, "argv", cmd)
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def _mutator_1(data):
    data["name"] = "invalid??"
    return data


def _mutator_2(data):
    data["name"] = "dash-invalid"
    return data


def _mutator_3(data):
    assert "contributions" in data
    c = data["contributions"]["commands"][0]["id"]
    data["contributions"]["commands"][0]["id"] = ".".join(
        ["not_packagename", *c.split(".")[1:]]
    )
    return data


def _mutator_4(data):
    assert "contributions" in data
    data["contributions"]["commands"][0]["python_name"] = "this.has.no.colon"
    return data


def _valid_mutator_no_contributions(data):
    """
    Contributions can be absent, in which case the Pydantic model will set the
    default value to None, and not the empty list, make sure that works.
    """
    del data["contributions"]
    return data


def _valid_mutator_no_contributions_None(data):
    """
    Contributions can be absent, in which case the Pydantic model will set the
    default value to None, and not the empty list, make sure that works.
    """
    data["contributions"] = None
    return data


def _mutator_no_contributes_extra_field(data):
    """
    Contributions used to be called contributes.

    Check that an extra field fails.
    """
    data["invalid_extra_name"] = data["contributions"]
    del data["contributions"]
    return data


@pytest.mark.parametrize(
    "mutator",
    [
        _mutator_1,
        _mutator_2,
        _mutator_3,
        _mutator_4,
        _mutator_no_contributes_extra_field,
    ],
)
def test_invalid(mutator, uses_sample_plugin):

    result = list(PluginManifest.discover())[0]
    assert result.error is None
    assert result.manifest is not None
    pm = result.manifest
    data = json.loads(pm.json(exclude_unset=True))
    mutator(data)
    with pytest.raises(ValidationError):
        PluginManifest(**data)


@pytest.mark.parametrize(
    "mutator",
    [_valid_mutator_no_contributions, _valid_mutator_no_contributions_None],
)
def test_valid_mutations(mutator, uses_sample_plugin):

    assert mutator.__name__.startswith("_valid")

    pm = list(PluginManifest.discover())[0]
    assert pm.manifest
    # make sure the data is a copy as we'll mutate it
    data = json.loads(pm.manifest.json(exclude_unset=True))
    mutator(data)

    PluginManifest(**data)
