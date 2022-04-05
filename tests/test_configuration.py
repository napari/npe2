from npe2 import PluginManager
from npe2.manifest.schema import PluginManifest

SAMPLE_PLUGIN_NAME = "my-plugin"

def test_configuration_empty():
    """ Ensures unpopulated configuration before plugin discovery. """
    pm = PluginManager()
    assert pm.configuration('check_str') == set()

def test_configuration_single_plugin(sample_manifest):
    """ Ensures populated configuration after plugin registry. """
    pm = PluginManager()
    pm.register(sample_manifest)
    assert pm.configuration('check_str') == {'foo'}
    assert pm.configuration('check_str_list') == {'a', 'b', 'c'}
    assert pm.configuration('check_num') == {10}
    assert pm.configuration('check_num_list') == {1, 2, 3}
    assert pm.configuration('check_bool') == {True}

def test_configuration_single_plugin_unregister(sample_manifest):
    """ Ensures unpopulated configuration after plugin unregistry. """
    pm = PluginManager()
    pm.register(sample_manifest)
    pm.unregister('my-plugin')
    assert pm.configuration('check_str') == set()

def test_configuration_multiple_plugins(sample_manifest):
    """ Ensures population for multiple plugins """
    pm = PluginManager()

    # Add a plugin
    pm.register(sample_manifest)
    assert pm.configuration('check_str') == {'foo'}

    # Add a second plugin
    manifest2 = PluginManifest(name = 'my-second-plugin', configuration={'check_str': 'bar'})
    pm.register(manifest2)
    # Ensure its configuration is appended
    assert pm.configuration('check_str') == {'foo', 'bar'}

    # Add a third plugin
    manifest3 = PluginManifest(name = 'my-third-plugin', configuration={'check_str': 'foo'})
    pm.register(manifest3)
    # Ensure its configuration is merged
    assert pm.configuration('check_str') == {'foo', 'bar'}