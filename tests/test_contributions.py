import json
from unittest.mock import Mock

import pytest

from npe2 import PluginManager, PluginManifest
from npe2.manifest.commands import CommandContribution
from npe2.manifest.sample_data import SampleDataGenerator, SampleDataURI

SAMPLE_PLUGIN_NAME = "my-plugin"


def test_writer_empty_layers():
    pm = PluginManager()
    pm.discover()
    writers = list(pm.iter_compatible_writers([]))
    assert not writers


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
def test_writer_ranges(param, uses_sample_plugin, plugin_manager: PluginManager):
    layer_types, expected_count = param
    nwriters = sum(
        w.command == f"{SAMPLE_PLUGIN_NAME}.my_writer"
        for w in plugin_manager.iter_compatible_writers(layer_types)
    )

    assert nwriters == expected_count


@pytest.mark.parametrize(
    "expr",
    ["vectors", "vectors+", "vectors*", "vectors?", "vectors{3}", "vectors{3,8}"],
)
def test_writer_valid_layer_type_expressions(expr, uses_sample_plugin):
    result = next(
        result
        for result in PluginManifest.discover()
        if result.manifest and result.manifest.name == SAMPLE_PLUGIN_NAME
    )
    assert result.error is None
    assert result.manifest is not None
    pm = result.manifest
    data = json.loads(pm.json(exclude_unset=True))

    assert "contributions" in data
    assert "writers" in data["contributions"]
    data["contributions"]["writers"][0]["layer_types"].append(expr)

    PluginManifest(**data)


def test_basic_iter_reader(uses_sample_plugin, plugin_manager: PluginManager, tmp_path):
    assert not list(plugin_manager.iter_compatible_readers(""))
    reader = list(plugin_manager.iter_compatible_readers(tmp_path))[0]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"

    reader = list(plugin_manager.iter_compatible_readers([tmp_path, tmp_path]))[0]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"

    with pytest.raises(ValueError):
        list(plugin_manager.iter_compatible_readers(["a.tif", "b.jpg"]))


def test_widgets(uses_sample_plugin, plugin_manager: PluginManager):
    from magicgui._magicgui import MagicFactory

    widgets = list(plugin_manager.iter_widgets())
    assert len(widgets) == 2
    assert widgets[0].command == f"{SAMPLE_PLUGIN_NAME}.some_widget"
    w = widgets[0].exec()
    assert type(w).__name__ == "SomeWidget"

    assert widgets[1].command == f"{SAMPLE_PLUGIN_NAME}.some_function_widget"
    w = widgets[1].get_callable()
    assert isinstance(w, MagicFactory)


def test_sample(uses_sample_plugin, plugin_manager: PluginManager):
    plugin, contribs = list(plugin_manager.iter_sample_data())[0]
    assert plugin == SAMPLE_PLUGIN_NAME
    assert len(contribs) == 2
    ctrbA, ctrbB = contribs
    # ignoring types because .command and .uri come from different sample provider
    # types... they don't both have "command" or "uri"
    assert isinstance(ctrbA, SampleDataGenerator)
    assert ctrbA.command == f"{SAMPLE_PLUGIN_NAME}.generate_random_data"
    assert ctrbA.plugin_name == SAMPLE_PLUGIN_NAME
    assert isinstance(ctrbB, SampleDataURI)
    assert ctrbB.uri == "https://picsum.photos/1024"
    assert isinstance(ctrbA.open(), list)
    assert isinstance(ctrbB.open(), list)


def test_directory_reader(uses_sample_plugin, plugin_manager: PluginManager, tmp_path):
    reader = list(plugin_manager.iter_compatible_readers(tmp_path))[0]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_themes(uses_sample_plugin, plugin_manager: PluginManager):
    theme = list(plugin_manager.iter_themes())[0]
    assert theme.label == "SampleTheme"


def test_command_exec():
    """Test CommandContribution.exec()"""
    pm = PluginManager.instance()
    try:
        cmd_id = "pkg.some_id"
        cmd = CommandContribution(id=cmd_id, title="a title")
        mf = PluginManifest(name="pkg", contributions={"commands": [cmd]})
        pm.register(mf)
        some_func = Mock()
        pm._command_registry.register(cmd_id, some_func)
        cmd.exec(args=("hi!",))
        some_func.assert_called_once_with("hi!")
    finally:
        pm.__instance = None
