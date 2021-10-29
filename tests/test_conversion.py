from npe2 import PluginManifest


def test_conversion():
    assert PluginManifest._from_npe1_plugin("svg")
