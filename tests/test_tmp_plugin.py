import pytest

from npe2 import DynamicPlugin, PluginManager
from npe2.manifest.contributions import SampleDataGenerator

TMP = "tmp"


@pytest.fixture
def tmp_plugin():
    local_pm = PluginManager()
    with DynamicPlugin(TMP, plugin_manager=local_pm) as tp:
        assert TMP in local_pm  # make sure it registered
        yield tp
    assert TMP not in local_pm  # make sure it cleaned up


def test_temporary_plugin(tmp_plugin: DynamicPlugin):
    """Test that we can use tmp_plugin to register commands for testing"""
    # everything is empty to begin with
    pm = tmp_plugin.plugin_manager
    contribs = tmp_plugin.manifest.contributions
    # everything is empty to begin with
    assert not contribs.commands
    assert not contribs.sample_data
    assert not contribs.readers
    assert not contribs.writers

    # we can populate with the contribute.x decorators

    @tmp_plugin.contribute.sample_data
    def make_image(x):
        return x

    @tmp_plugin.contribute.reader
    def read_path(path):
        ...

    # can override args
    ID = f"{TMP}.random_id"

    @tmp_plugin.contribute.command(id=ID)
    def some_command():
        return "hi!"

    # some require args

    with pytest.raises(AssertionError) as e:

        @tmp_plugin.contribute.writer
        def write_path_bad(path, layer_data):
            ...

    assert "layer_types must not be empty" in str(e.value)
    # it didn't get added
    assert "tmp.write_path_bad" not in pm.commands

    @tmp_plugin.contribute.writer(layer_types=["image"])
    def write_path(path, layer_data):
        ...

    # now it did
    assert "tmp.write_path" in pm.commands

    # contributions have been populated
    assert contribs.commands
    assert contribs.sample_data
    assert contribs.readers
    assert contribs.writers

    # and the commands work
    samples = next(contribs for plg, contribs in pm.iter_sample_data() if plg == TMP)
    gen = samples[0]
    assert isinstance(gen, SampleDataGenerator)
    assert gen.exec((1,), _registry=pm.commands) == 1

    cmd = pm.get_command(ID)
    assert cmd.exec(_registry=pm.commands) == "hi!"


def test_temporary_plugin_change_pm(tmp_plugin: DynamicPlugin):
    """We can change the plugin manager we're assigned to.

    Probably not necessary, but perhaps useful in tests.
    """
    start_pm = tmp_plugin.plugin_manager
    new_pm = PluginManager()

    @tmp_plugin.contribute.command
    def some_command():
        return "hi!"

    assert "tmp.some_command" in start_pm.commands
    assert "tmp.some_command" not in new_pm.commands

    tmp_plugin.plugin_manager = new_pm

    assert "tmp.some_command" not in start_pm.commands
    assert "tmp.some_command" in new_pm.commands

    tmp_plugin.clear()
    assert not tmp_plugin.manifest.contributions.commands


def test_temporary_plugin_spawn(tmp_plugin: DynamicPlugin):
    new = tmp_plugin.spawn("another-name", register=True)
    assert new.name == "another-name"
    assert new.display_name == "another-name"
    assert new.plugin_manager == tmp_plugin.plugin_manager

    assert (t1 := tmp_plugin.spawn(register=True)).name == f"{tmp_plugin.name}-1"
    assert (t2 := tmp_plugin.spawn()).name == f"{tmp_plugin.name}-2"

    assert t1.name in tmp_plugin.plugin_manager._manifests
    assert t2.name not in tmp_plugin.plugin_manager._manifests
