import sys

import pytest

from npe2._command_registry import CommandHandler, CommandRegistry
from npe2._plugin_manager import PluginManager
from npe2.manifest.schema import PluginManifest

SAMPLE_PLUGIN_NAME = "my-plugin"


@pytest.fixture
def pm(sample_path):

    pm = PluginManager()
    pm.discover()
    assert len(pm._manifests) == 0
    sys.path.append(str(sample_path))
    try:
        pm.discover()
        yield pm
    finally:
        sys.path.remove(str(sample_path))


def test_plugin_manager(pm: PluginManager):
    assert pm.get_command(f"{SAMPLE_PLUGIN_NAME}.hello_world")

    assert SAMPLE_PLUGIN_NAME not in pm._contexts
    ctx = pm.activate(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME in pm._contexts
    assert pm.get_manifest(SAMPLE_PLUGIN_NAME)

    # dual activation is prevented
    assert pm.activate(SAMPLE_PLUGIN_NAME) is ctx

    assert pm.get_command(f"{SAMPLE_PLUGIN_NAME}.hello_world")

    assert pm.get_submenu("mysubmenu")
    assert len(list(pm.iter_menu("/napari/layer_context"))) == 2

    # deactivation
    assert SAMPLE_PLUGIN_NAME in pm._contexts
    pm.deactivate(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME not in pm._contexts
    pm.deactivate(SAMPLE_PLUGIN_NAME)  # second time is a no-op
    assert SAMPLE_PLUGIN_NAME not in pm._contexts


def test_plugin_manager_raises(pm: PluginManager):
    with pytest.raises(KeyError):
        pm.get_manifest("not-a-pluginxxx")
    with pytest.raises(KeyError):
        pm.activate("not a thing")
    with pytest.raises(KeyError):
        pm.get_command(f"{SAMPLE_PLUGIN_NAME}.not_a_thing")
    with pytest.raises(ValueError) as e:
        pm.register(PluginManifest(name=SAMPLE_PLUGIN_NAME))
    assert f"A manifest with name {SAMPLE_PLUGIN_NAME!r} already" in str(e.value)


def test_command_handler():
    with pytest.raises(RuntimeError):
        # cannot resolve something without either a python_name or function
        CommandHandler("hi").resolve()

    with pytest.raises(RuntimeError):
        # cannot resolve something without either a python_name or function
        CommandHandler("hi", python_name="cannot.import.this").resolve()


def test_command_reg_register():
    reg = CommandRegistry()
    with pytest.raises(ValueError):
        # must register non empty string id
        reg.register(1, lambda: None)  # type: ignore
    with pytest.raises(TypeError):
        # neither a string or a callable
        reg.register("other.id", 8)  # type: ignore

    with pytest.raises(ValueError):
        # must register non empty string id
        reg.register("some.id", "1_is_not.a_valid_python_name")
    reg.register("some.id", "this.is.a_valid_python_name")

    with pytest.raises(ValueError):
        # already registered
        reg.register("some.id", "this.is.a_valid_python_name")

    with pytest.raises(KeyError) as e:
        reg.get("not.a.command")
    assert "command 'not.a.command' not registered" in str(e.value)


def test_command_reg_get():
    def f(x, y):
        return x + y

    reg = CommandRegistry()
    reg.register("id", f)
    assert "id" in reg
    assert reg.get("id") is f
    assert reg.execute("id", (1, 2)) == 3
