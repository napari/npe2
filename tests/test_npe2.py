import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import npe2
from npe2 import PluginManifest
from npe2._plugin_manager import PluginManager

SAMPLE = Path(__file__).parent / "sample"


@pytest.fixture
def uses_sample_plugin():
    sys.path.append(str(SAMPLE))
    yield
    sys.path.remove(str(SAMPLE))


@pytest.fixture
def isolated_plugin_manager(uses_sample_plugin):
    pm = PluginManager()
    pm.discover(filter_by_key={"publisher.my_plugin"})
    return pm


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path
    manifests = list(
        result.manifest.name for result in PluginManifest.discover() if result.manifest
    )
    assert "my_plugin" not in manifests


def test_discover(uses_sample_plugin):
    manifests = list(
        result.manifest.name for result in PluginManifest.discover() if result.manifest
    )
    assert "my_plugin" in manifests


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


def _mutator_writer_requires_non_empty_layer_types(data):
    data["contributions"]["writers"][0]["layer_types"] = []
    return data


def _mutator_writer_invalid_layer_type_constraint(data):
    data["contributions"]["writers"][0]["layer_types"].append("image{")
    return data


def _mutator_writer_invalid_file_extension_1(data):
    data["contributions"]["writers"][0]["filename_extensions"] = ["*"]
    return data


def _mutator_writer_invalid_file_extension_2(data):
    print(f'HERE {data["contributions"]["writers"][0]["filename_extensions"]}')
    data["contributions"]["writers"][0]["filename_extensions"] = ["."]
    return data


@pytest.mark.parametrize(
    "mutator",
    [
        _mutator_1,
        _mutator_2,
        _mutator_3,
        _mutator_4,
        _mutator_no_contributes_extra_field,
        _mutator_writer_requires_non_empty_layer_types,
        _mutator_writer_invalid_layer_type_constraint,
        _mutator_writer_invalid_file_extension_1,
        _mutator_writer_invalid_file_extension_2,
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


def test_writer_empty_layers(uses_sample_plugin):
    pm = PluginManager()
    pm.discover()

    writers = list(pm.iter_compatible_writers([]))
    assert len(writers) == 0


@pytest.mark.parametrize(
    "param",
    [
        (["image"] * 2, 1),
        (["labels"], 0),
        (["image"] * 4, 1),
        (["image"] * 5, 0),
        (["points", "surface"], 1),
        (["points", "surface", "points"], 0),
    ],
)
def test_writer_ranges(param, isolated_plugin_manager):
    pm = isolated_plugin_manager

    layer_types, expected_count = param
    nwriters = sum(
        w.command == "my_plugin.my_writer"
        for w in pm.iter_compatible_writers(layer_types)
    )

    assert nwriters == expected_count


@pytest.mark.parametrize(
    "expr",
    [
        "vectors{",
        "image",  # should parse fine, but be a duplication error
        "vectors{8,3}",
        "vectors{-1}",
        "vectors??",
        "other?",
    ],
)
def test_writer_invalid_layer_type_expressions(expr, uses_sample_plugin):
    result = next(
        result
        for result in PluginManifest.discover()
        if result.manifest and result.manifest.name == "my_plugin"
    )
    assert result.error is None
    assert result.manifest is not None
    pm = result.manifest
    data = json.loads(pm.json(exclude_unset=True))

    assert "contributions" in data
    assert "writers" in data["contributions"]
    data["contributions"]["writers"][0]["layer_types"].append(expr)

    with pytest.raises(ValidationError):
        PluginManifest(**data)


@pytest.mark.parametrize(
    "expr",
    ["vectors", "vectors+", "vectors*", "vectors?", "vectors{3}", "vectors{3,8}"],
)
def test_writer_valid_layer_type_expressions(expr, uses_sample_plugin):
    result = next(
        result
        for result in PluginManifest.discover()
        if result.manifest and result.manifest.name == "my_plugin"
    )
    assert result.error is None
    assert result.manifest is not None
    pm = result.manifest
    data = json.loads(pm.json(exclude_unset=True))

    assert "contributions" in data
    assert "writers" in data["contributions"]
    data["contributions"]["writers"][0]["layer_types"].append(expr)

    PluginManifest(**data)


@pytest.mark.parametrize(
    "layer_data",
    [
        [
            (None, {}, "image"),
            (None, {}, "image"),
        ],
        [],
    ],
)
def test_writer_exec(layer_data, isolated_plugin_manager):
    writer = next(
        isolated_plugin_manager.iter_compatible_writers(["image", "image"]), None
    )
    assert writer is not None
    # This writer doesn't do anything but type check.
    paths = npe2.write_layers(writer, "test/path", layer_data)
    assert len(paths) == 1


def test_writer_single_layer_api_exec(isolated_plugin_manager):
    writer = next(isolated_plugin_manager.iter_compatible_writers(["labels"]), None)
    assert writer is not None
    # This writer doesn't do anything but type check.
    paths = npe2.write_layers(writer, "test/path", [(None, {}, "labels")])
    assert len(paths) == 1
