import pytest

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
