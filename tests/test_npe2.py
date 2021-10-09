import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from npe2 import PluginManifest
from npe2._plugin_manager import PluginManager

SAMPLE = Path(__file__).parent / "sample"


@pytest.fixture
def uses_sample_plugin():
    sys.path.append(str(SAMPLE))
    yield
    sys.path.remove(str(SAMPLE))


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path
    manifests = list(
        result.manifest for result in PluginManifest.discover() if result.manifest
    )
    names = [m.name for m in manifests]
    assert "my_plugin" not in names


def test_discover(uses_sample_plugin):
    manifests = list(
        result.manifest for result in PluginManifest.discover() if result.manifest
    )
    names = [m.name for m in manifests]
    assert "my_plugin" in names


def test_plugin_manager(uses_sample_plugin):
    pm = PluginManager()
    pm.discover()
    assert len(pm._manifests) > 0
    pm.activate("publisher.my_plugin")


def test_cli(monkeypatch):
    from npe2.cli import main

    cmd = ["npe2", "validate", str(SAMPLE / "my_plugin" / "napari.yaml")]
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
    result = next(
        result
        for result in PluginManifest.discover()
        if result.manifest and result.manifest.name == "my_plugin"
    )
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

    pm = next(
        result.manifest
        for result in PluginManifest.discover()
        if result.manifest and result.manifest.name == "my_plugin"
    )

    # make sure the data is a copy as we'll mutate it
    data = json.loads(pm.json(exclude_unset=True))
    mutator(data)

    PluginManifest(**data)
