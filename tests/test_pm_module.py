from npe2 import PluginManager


def test_pm_module():
    from npe2 import plugin_manager as pm

    assert pm.instance() is PluginManager.instance()

    # smoke-test checking that a few of the argument-free things work
    # they may or may-not be empty depending on other tests in this suite.
    pm.iter_widgets()
    pm.iter_sample_data()

    # make sure we have it covered.
    for k, v in vars(PluginManager).items():
        if k.startswith("_") or isinstance(v, (classmethod, property)):
            continue
        assert hasattr(pm, k), f"pm.py module is missing function {k!r}"
