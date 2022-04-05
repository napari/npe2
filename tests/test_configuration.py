from npe2 import PluginManager
from npe2.manifest.schema import PluginManifest

SAMPLE_PLUGIN_NAME = "my-plugin"


def test_properties_empty():
    """Ensures unpopulated properties before plugin discovery."""
    pm = PluginManager()
    assert pm.properties("check_str") == set()


def test_properties_single_plugin(sample_manifest):
    """Ensures populated properties after plugin registry."""
    pm = PluginManager()
    pm.register(sample_manifest)
    assert pm.properties("check_str") == {"foo"}
    assert pm.properties("check_str_list") == {"a", "b", "c"}
    assert pm.properties("check_num") == {10}
    assert pm.properties("check_num_list") == {1, 2, 3}
    assert pm.properties("check_bool") == {True}


def test_properties_single_plugin_unregister(sample_manifest):
    """Ensures unpopulated properties after plugin unregistry."""
    pm = PluginManager()
    pm.register(sample_manifest)
    pm.unregister("my-plugin")
    assert pm.properties("check_str") == set()


def test_properties_multiple_plugins(sample_manifest):
    """Ensures population for multiple plugins"""
    pm = PluginManager()

    # Add a plugin
    pm.register(sample_manifest)
    assert pm.properties("check_str") == {"foo"}

    # Add a second plugin
    manifest2 = PluginManifest(name="my-second-plugin", properties={"check_str": "bar"})
    pm.register(manifest2)
    # Ensure its properties is appended
    assert pm.properties("check_str") == {"foo", "bar"}

    # Add a third plugin
    manifest3 = PluginManifest(name="my-third-plugin", properties={"check_str": "foo"})
    pm.register(manifest3)
    # Ensure its properties is merged
    assert pm.properties("check_str") == {"foo", "bar"}
