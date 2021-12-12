import pytest

from npe2._command_registry import CommandHandler, CommandRegistry
from npe2._plugin_manager import PluginManager


def test_plugin_manager(sample_path):
    pm = PluginManager()
    pm.discover()
    assert len(pm._manifests) == 0
    pm.discover([sample_path])
    assert len(pm._manifests) == 1
    assert pm.get_command("my_plugin.hello_world")

    assert "my_plugin" not in pm._contexts
    ctx = pm.activate("my_plugin")
    assert "my_plugin" in pm._contexts

    # dual activation is prevented
    assert pm.activate("my_plugin") is ctx

    with pytest.raises(KeyError):
        pm.activate("not a thing")

    assert pm.get_command("my_plugin.hello_world")
    with pytest.raises(KeyError):
        pm.get_command("my_plugin.not_a_thing")

    assert pm.get_submenu("mysubmenu")
    assert len(list(pm.iter_menu("/napari/layer_context"))) == 2

    # deactivation
    assert "my_plugin" in pm._contexts
    pm.deactivate("my_plugin")
    assert "my_plugin" not in pm._contexts
    pm.deactivate("my_plugin")  # second time is a no-op
    assert "my_plugin" not in pm._contexts


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


def test_command_reg_get():
    def f(x, y):
        return x + y

    reg = CommandRegistry()
    reg.register("id", f)
    assert "id" in reg
    assert reg.get("id") is f
    assert reg.execute("id", (1, 2)) == 3
