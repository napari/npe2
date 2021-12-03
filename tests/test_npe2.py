import json
import sys

import pytest
from pydantic import ValidationError

from npe2 import PluginManager, PluginManifest
from npe2.cli import main


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path
    manifests = [
        result.manifest.name for result in PluginManifest.discover() if result.manifest
    ]

    assert "my_plugin" not in manifests


def test_sample_plugin_valid(sample_path):
    assert PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")


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

    pm = list(PluginManifest.discover())[0]
    assert pm.manifest
    # make sure the data is a copy as we'll mutate it
    data = json.loads(pm.manifest.json(exclude_unset=True))
    mutator(data)

    PluginManifest(**data)


@pytest.mark.parametrize(
    "display_name",
    [
        "Here there everywhere and more with giggles and friends",
        "ab",
        " abc",
        "abc ",
        "_abc",
        "abc_",
        "abc♱",
    ],
)
def test_invalid_display_names(display_name, uses_sample_plugin):
    field = PluginManifest.__fields__["display_name"]
    value, err = field.validate(display_name, {}, loc="display_name")
    assert err is not None


@pytest.mark.parametrize(
    "display_name",
    [
        "Some Cell & Stru买cture Segmenter",
        "Segment Blobs and Things with Membranes",
        "abc",
        "abc䜁䜂",
    ],
)
def test_valid_display_names(display_name, uses_sample_plugin):
    field = PluginManifest.__fields__["display_name"]
    value, err = field.validate(display_name, {}, loc="display_name")
    assert err is None


def test_display_name_default_is_valid():
    PluginManifest(name="", entry_point="")


def test_writer_empty_layers():
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
def test_writer_ranges(param, plugin_manager: PluginManager):
    layer_types, expected_count = param
    nwriters = sum(
        w.command == "my_plugin.my_writer"
        for w in plugin_manager.iter_compatible_writers(layer_types)
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


def test_widget(uses_sample_plugin, plugin_manager: PluginManager):
    contrib = list(plugin_manager.iter_widgets())[0]
    assert contrib.command == "my_plugin.some_widget"
    w = contrib.exec()
    assert type(w).__name__ == "SomeWidget"


def test_sample(uses_sample_plugin, plugin_manager: PluginManager):
    plugin, contribs = list(plugin_manager.iter_sample_data())[0]
    assert plugin == "my_plugin"
    assert len(contribs) == 2
    ctrbA, ctrbB = contribs
    # ignoring types because .command and .uri come from different sample provider
    # types... they don't both have "command" or "uri"
    assert ctrbA.command == "my_plugin.generate_random_data"
    assert ctrbB.uri == "https://picsum.photos/1024"
    assert isinstance(ctrbA.open(), list)
    assert isinstance(ctrbB.open(), list)


def test_toml_round_trip(sample_path, tmp_path):
    pm = PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")

    toml_file = tmp_path / "napari.toml"
    toml_file.write_text(pm.toml())

    pm2 = PluginManifest.from_file(toml_file)
    assert pm == pm2


def test_json_round_trip(sample_path, tmp_path):
    pm = PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")

    json_file = tmp_path / "napari.json"
    json_file.write_text(pm.json())

    pm2 = PluginManifest.from_file(json_file)
    assert pm == pm2
