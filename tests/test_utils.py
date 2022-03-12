import pytest

from npe2.manifest.schema import PluginManifest
from npe2.manifest.utils import Version, merge_manifests


def test_version():
    v = Version.parse(b"0.1.2")

    assert v == "0.1.2"
    assert v > dict(major=0, minor=1, patch=0)
    assert v <= (0, 2, 0)
    assert v == Version(0, 1, 2)
    assert list(v) == [0, 1, 2, None, None]
    assert str(v) == "0.1.2"

    with pytest.raises(TypeError):
        v == 1.2

    with pytest.raises(ValueError):
        Version.parse("alkfdjs")

    with pytest.raises(TypeError):
        Version.parse(1.2)  # type: ignore


def test_merge_manifests():
    with pytest.raises(ValueError):
        merge_manifests([])

    with pytest.raises(AssertionError) as e:
        merge_manifests([PluginManifest(name="p1"), PluginManifest(name="p2")])
    assert "All manifests must have same name" in str(e.value)

    pm1 = PluginManifest(
        name="plugin",
        contributions={
            "commands": [{"id": "plugin.command", "title": "some writer"}],
            "writers": [{"command": "plugin.command", "layer_types": ["image"]}],
        },
    )
    pm2 = PluginManifest(
        name="plugin",
        contributions={
            "commands": [{"id": "plugin.command", "title": "some reader"}],
            "readers": [{"command": "plugin.command", "filename_patterns": [".tif"]}],
        },
    )
    expected_merge = PluginManifest(
        name="plugin",
        contributions={
            "commands": [
                {"id": "plugin.command", "title": "some writer"},
                {"id": "plugin.command_2", "title": "some reader"},  # no dupes
            ],
            "writers": [{"command": "plugin.command", "layer_types": ["image"]}],
            "readers": [{"command": "plugin.command_2", "filename_patterns": [".tif"]}],
        },
    )

    assert merge_manifests([pm1]) is pm1
    assert merge_manifests([pm1, pm2]) == expected_merge
