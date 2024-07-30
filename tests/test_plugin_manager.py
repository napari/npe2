import sys
from unittest.mock import Mock, patch

import pytest

from npe2._command_registry import CommandHandler, CommandRegistry
from npe2._plugin_manager import PluginManager
from npe2.manifest.schema import PluginManifest
from npe2.types import PythonName

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


def test_discover_clear(uses_sample_plugin):
    pm = PluginManager.instance()
    assert SAMPLE_PLUGIN_NAME in pm._manifests
    reg_mock = Mock()
    pm.events.plugins_registered.connect(reg_mock)
    with patch.object(pm, "register", wraps=pm.register) as mock:
        pm.discover()
        mock.assert_not_called()  # nothing new to register
        reg_mock.assert_not_called()

        mock.reset_mock()
        pm.discover(clear=True)  # clear forces reregister
        mock.assert_called_once()
        reg_mock.assert_called_once_with({pm._manifests[SAMPLE_PLUGIN_NAME]})


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
    with pytest.raises(KeyError):
        pm.get_submenu("not-a-submenu")
    assert len(list(pm.iter_menu("/napari/layer_context"))) == 2

    # deactivation
    assert SAMPLE_PLUGIN_NAME in pm._contexts
    pm.deactivate(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME not in pm._contexts
    pm.deactivate(SAMPLE_PLUGIN_NAME)  # second time is a no-op
    assert SAMPLE_PLUGIN_NAME not in pm._contexts


def test_plugin_manager_register(sample_path):
    sys.path.append(str(sample_path))
    try:
        pm = PluginManager()
        pm.register(str(sample_path / "my_plugin" / "napari.yaml"))
        assert "my-plugin" in pm._manifests
        pm.unregister("my-plugin")
        assert "my-plugin" not in pm._manifests
        pm.register("my_plugin")
        assert "my-plugin" in pm._manifests
    finally:
        sys.path.remove(str(sample_path))


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
        CommandHandler("hi", python_name=PythonName("cannot.import.this")).resolve()


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


def _assert_sample_enabled(plugin_manager: PluginManager, enabled=True):
    i = SAMPLE_PLUGIN_NAME in plugin_manager._contrib._indexed
    assert i if enabled else not i

    _not = "not " if not enabled else ""
    # command
    if enabled:
        assert plugin_manager.get_command(f"{SAMPLE_PLUGIN_NAME}.hello_world")
    else:
        with pytest.raises(KeyError):
            assert plugin_manager.get_command(f"{SAMPLE_PLUGIN_NAME}.hello_world")

    # reader
    cmds = [r.command for r in plugin_manager.iter_compatible_readers("*.fzy")]
    b = f"{SAMPLE_PLUGIN_NAME}.some_reader" in cmds
    assert b if enabled else not b, f"Reader should {_not}be enabled"

    # writer
    cmds = [r.command for r in plugin_manager.iter_compatible_writers(["image"] * 2)]
    c = f"{SAMPLE_PLUGIN_NAME}.my_writer" in cmds
    assert c if enabled else not c, f"Writer should {_not}be enabled"

    d = "SampleTheme" in [t.label for t in plugin_manager.iter_themes()]
    assert d if enabled else not d, f"Theme should {_not}be enabled"


def test_enable_disable(uses_sample_plugin, plugin_manager: PluginManager, tmp_path):
    _assert_sample_enabled(plugin_manager)
    # just to test the enabled= kwarg on iter_manifests
    # (this would show *only* disabled plugins)
    assert not list(plugin_manager.iter_manifests(disabled=True))

    # Do disable
    mock = Mock()
    plugin_manager.events.enablement_changed.connect(mock)
    plugin_manager.disable(SAMPLE_PLUGIN_NAME)
    mock.assert_called_once_with({}, {SAMPLE_PLUGIN_NAME})  # enabled, disabled

    _assert_sample_enabled(plugin_manager, False)

    # stuff you can't do while disabled:
    with pytest.raises(ValueError):
        plugin_manager.activate(SAMPLE_PLUGIN_NAME)

    # re-enable
    mock.reset_mock()
    plugin_manager.enable(SAMPLE_PLUGIN_NAME)
    mock.assert_called_once_with({SAMPLE_PLUGIN_NAME}, {})  # enabled, disabled
    _assert_sample_enabled(plugin_manager)


def test_warn_on_register_disabled(uses_sample_plugin, plugin_manager: PluginManager):
    assert SAMPLE_PLUGIN_NAME in plugin_manager
    mf = plugin_manager[SAMPLE_PLUGIN_NAME]
    plugin_manager.disable(SAMPLE_PLUGIN_NAME)
    plugin_manager._manifests.pop(SAMPLE_PLUGIN_NAME)  # NOT good way to "unregister"
    with pytest.warns(UserWarning):
        plugin_manager.register(mf)


def test_plugin_manager_dict(uses_sample_plugin, plugin_manager: PluginManager):
    """Test exporting the plugin manager state with `dict()`."""
    d = plugin_manager.dict()
    assert SAMPLE_PLUGIN_NAME in d["plugins"]
    assert "disabled" in d
    assert "activated" in d

    d = plugin_manager.dict(
        include={"contributions", "package_metadata.version"},
        exclude={"contributions.writers", "contributions.readers"},
    )
    plugin_dict = d["plugins"][SAMPLE_PLUGIN_NAME]
    assert set(plugin_dict) == {"contributions", "package_metadata"}
    contribs = set(plugin_dict["contributions"])
    assert "readers" not in contribs
    assert "writers" not in contribs


def test_plugin_context_dispose():
    pm = PluginManager()
    mf = PluginManifest(name="test")
    pm.register(mf)
    mock = Mock()
    pm.get_context("test").register_disposable(mock)
    pm.deactivate("test")
    mock.assert_called_once()


def test_plugin_context_dispose_error(caplog):
    """Test errors when executing dispose functions caught correctly."""
    pm = PluginManager()
    mf = PluginManifest(name="test")
    pm.register(mf)

    def dummy_error():
        raise ValueError("This is an error")

    pm.get_context("test").register_disposable(dummy_error)
    pm.deactivate("test")
    assert caplog.records[0].msg == "Error while disposing test; This is an error"


def test_command_menu_map(uses_sample_plugin, plugin_manager: PluginManager):
    """Test that the command menu map is correctly populated."""
    pm = PluginManager.instance()
    assert SAMPLE_PLUGIN_NAME in pm._manifests
    assert SAMPLE_PLUGIN_NAME in pm._command_menu_map

    # contains correct commands
    command_menu_map = pm._command_menu_map[SAMPLE_PLUGIN_NAME]
    assert "my-plugin.hello_world" in command_menu_map
    assert "my-plugin.another_command" in command_menu_map

    # commands point to correct menus
    assert len(cmd_menu := command_menu_map["my-plugin.hello_world"]) == 1
    assert "/napari/layer_context" in cmd_menu
    assert len(cmd_menu := command_menu_map["my-plugin.another_command"]) == 1
    assert "mysubmenu" in cmd_menu

    # enable/disable
    pm.disable(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME not in pm._command_menu_map
    pm.enable(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME in pm._command_menu_map

    # register/unregister
    pm.unregister(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME not in pm._command_menu_map
    pm.register(SAMPLE_PLUGIN_NAME)
    assert SAMPLE_PLUGIN_NAME in pm._command_menu_map
