import json
from functools import partial
from unittest.mock import Mock

import pytest

from npe2 import DynamicPlugin, PluginManager, PluginManifest
from npe2.manifest.contributions import (
    CommandContribution,
    SampleDataGenerator,
    SampleDataURI,
)

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


def test_writer_priority():
    """Contributions listed earlier in the manifest should be preferred."""
    pm = PluginManager()
    with DynamicPlugin(name="my_plugin", plugin_manager=pm) as plg:

        @plg.contribute.writer(filename_extensions=["*.tif"], layer_types=["image"])
        def my_writer1(path, data):
            ...

        @plg.contribute.writer(filename_extensions=["*.abc"], layer_types=["image"])
        def my_writer2(path, data):
            ...

        writers = list(pm.iter_compatible_writers(["image"]))
        assert writers[0].command == "my_plugin.my_writer1"
        assert len(pm) == 1


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
    tmp_path = str(tmp_path)
    assert not list(plugin_manager.iter_compatible_readers(""))
    reader = next(iter(plugin_manager.iter_compatible_readers(tmp_path)))
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"

    reader = next(iter(plugin_manager.iter_compatible_readers([tmp_path, tmp_path])))
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"

    with pytest.raises(ValueError):
        list(plugin_manager.iter_compatible_readers(["a.tif", "b.jpg"]))


def test_widgets(uses_sample_plugin, plugin_manager: PluginManager):
    widgets = list(plugin_manager.iter_widgets())
    assert len(widgets) == 2
    assert widgets[0].command == f"{SAMPLE_PLUGIN_NAME}.some_widget"
    w = widgets[0].exec()
    assert type(w).__name__ == "SomeWidget"

    assert widgets[1].command == f"{SAMPLE_PLUGIN_NAME}.some_function_widget"
    w = widgets[1].get_callable()
    assert isinstance(w, partial)


def test_sample(uses_sample_plugin, plugin_manager: PluginManager):
    plugin, contribs = next(iter(plugin_manager.iter_sample_data()))
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
    reader = next(iter(plugin_manager.iter_compatible_readers(str(tmp_path))))
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_themes(uses_sample_plugin, plugin_manager: PluginManager):
    theme = next(iter(plugin_manager.iter_themes()))
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


def test_menus(uses_sample_plugin, plugin_manager: PluginManager):
    menus = plugin_manager.menus()
    assert len(menus) == 2
    assert set(menus) == {"/napari/layer_context", "mysubmenu"}
    items = list(plugin_manager.iter_menu("/napari/layer_context"))
    assert len(items) == 2
