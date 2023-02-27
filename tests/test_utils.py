import pytest

from npe2.manifest.contributions import ContributionPoints
from npe2.manifest.schema import PluginManifest
from npe2.manifest.utils import (
    Version,
    deep_update,
    merge_contributions,
    merge_manifests,
)


def test_version():
    v = Version.parse(b"0.1.2")

    assert v == "0.1.2"
    assert v > {"major": 0, "minor": 1, "patch": 0}
    assert v <= (0, 2, 0)
    assert v == Version(0, 1, 2)
    assert list(v) == [0, 1, 2, None, None]
    assert str(v) == "0.1.2"

    with pytest.raises(TypeError):
        assert v == 1.2

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


def test_merge_contributions():
    a = ContributionPoints(
        commands=[
            {"id": "plugin.command", "title": "some writer"},
        ],
        writers=[{"command": "plugin.command", "layer_types": ["image"]}],
    )
    b = ContributionPoints(
        commands=[
            {"id": "plugin.command", "title": "some writer"},
        ],
        writers=[{"command": "plugin.command", "layer_types": ["image"]}],
    )
    c = ContributionPoints(
        commands=[
            {"id": "plugin.command", "title": "some writer"},
        ],
        writers=[{"command": "plugin.command", "layer_types": ["image"]}],
    )
    expected = ContributionPoints(
        commands=[
            {"id": "plugin.command", "title": "some writer"},
            {"id": "plugin.command_2", "title": "some writer"},
            {"id": "plugin.command_3", "title": "some writer"},
        ],
        writers=[
            {"command": "plugin.command", "layer_types": ["image"]},
            {"command": "plugin.command_2", "layer_types": ["image"]},
            {"command": "plugin.command_3", "layer_types": ["image"]},
        ],
    )

    d = ContributionPoints(**merge_contributions((a, b, c)))
    assert d == expected

    # with overwrite, later contributions with matching command ids take precendence.
    e = ContributionPoints(**merge_contributions((a, b, c), overwrite=True))
    expected = ContributionPoints(
        commands=[
            {"id": "plugin.command", "title": "some writer"},
        ],
        writers=[
            {"command": "plugin.command", "layer_types": ["image"]},
        ],
    )
    assert e == a


def test_deep_update():
    a = {"a": {"b": 1, "c": 2}, "e": 2}
    b = {"a": {"d": 4, "c": 3}, "f": 0}
    c = deep_update(a, b, copy=True)
    assert c == {"a": {"b": 1, "d": 4, "c": 3}, "e": 2, "f": 0}
    assert a == {"a": {"b": 1, "c": 2}, "e": 2}

    deep_update(a, b, copy=False)
    assert a == {"a": {"b": 1, "d": 4, "c": 3}, "e": 2, "f": 0}
