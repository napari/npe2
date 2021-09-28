import sys
from pathlib import Path

import pytest

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


def test_discover(uses_sample_plugin):
    assert len(list(PluginManifest.discover())) == 1


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
