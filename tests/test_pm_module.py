from npe2 import PluginManager


def test_pm_module():
    from npe2 import pm

    assert pm.instance() is PluginManager.instance()

    # just checking that a few of the argument-free things work
    assert not list(pm.iter_widgets())
    assert not list(pm.iter_sample_data())
    assert not list(pm.iter_compatible_readers("sadfds"))
