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
    manifests = list(PluginManifest.discover())
    assert len(manifests) == 0


def test_discover(uses_sample_plugin):
    manifests = list(PluginManifest.discover())
    assert len(manifests) == 1
    assert manifests[0].name == "my_plugin"


def test_plugin_manager(uses_sample_plugin):
    pm = PluginManager()
    pm.discover()
    assert len(pm._manifests) == 1
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
    assert "contributes" in data
    c = data["contributes"]["commands"][0]["command"]
    data["contributes"]["commands"][0]["command"] = ".".join(
        ["not_packagename", *c.split(".")[1:]]
    )
    return data


def _mutator_4(data):
    assert "contributes" in data
    data["contributes"]["commands"][0]["python_name"] = "this.has.no.colon"
    return data


@pytest.mark.parametrize("mutator", [_mutator_1, _mutator_2, _mutator_3, _mutator_4])
def test_invalid(mutator, uses_sample_plugin):

    import json

    pm = list(PluginManifest.discover())[0]
    data = json.loads(pm.json(exclude_unset=True))
    mutator(data)
    with pytest.raises(ValidationError):
        PluginManifest(**data)
