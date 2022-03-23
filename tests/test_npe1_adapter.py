from functools import partial
from unittest.mock import patch

import numpy as np
import pytest
from magicgui._magicgui import MagicFactory

from npe2 import PluginManager
from npe2.manifest import _npe1_adapter, utils
from npe2.manifest.sample_data import SampleDataGenerator

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


def test_shim_no_npe1():
    pm = PluginManager()
    pm.discover()
    assert not pm._shims


def test_npe1_shim(uses_npe1_plugin):
    """Test that the plugin manager detects npe1 plugins, and can index contribs"""
    pm = PluginManager()
    pm.discover()

    # we've found a shim
    assert len(pm._shims) == 1
    mf = pm.get_manifest("npe1-plugin")
    assert isinstance(mf, _npe1_adapter.NPE1Adapter)
    assert mf.package_metadata
    assert mf.package_metadata.version == "0.1.0"
    assert mf.package_metadata.name == "npe1-plugin"

    # it's currently unindexed and unstored

    with patch.object(
        _npe1_adapter,
        "manifest_from_npe1",
        wraps=_npe1_adapter.manifest_from_npe1,  # type: ignore
    ) as mock:
        pm.index_npe1_shims()
        # the shim has been cleared by the indexing
        assert len(pm._shims) == 0
        # manifest_from_npe1 was called
        mock.assert_called_once_with(mf._dist, shim=True)
        # NOTE: accessing the `.contributions` object would have also triggered
        # importing, like pm.index_npe1_shims() above, but it would not have
        # injected the contributions into the pm._contrib object.
        assert mf.contributions.sample_data


def _get_mf() -> _npe1_adapter.NPE1Adapter:
    pm = PluginManager.instance()
    pm.discover()
    pm.index_npe1_shims()
    mf = pm.get_manifest("npe1-plugin")
    assert isinstance(mf, _npe1_adapter.NPE1Adapter)
    return mf


def test_shim_pyname_sample_data(uses_npe1_plugin):
    """Test that objects defined locally in npe1 hookspecs can be retrieved."""
    mf = _get_mf()
    samples = mf.contributions.sample_data
    assert samples
    sample_generator = next(s for s in samples if s.key == "local_data")
    assert isinstance(sample_generator, SampleDataGenerator)

    ONES = np.ones((4, 4))
    with patch.object(utils, "_import_npe1_shim", wraps=utils._import_npe1_shim) as m:
        func = sample_generator.get_callable()
        assert isinstance(func, partial)  # this is how it was defined in npe1-plugin
        pyname = "__npe1shim__.npe1_module:napari_provide_sample_data_1"
        m.assert_called_once_with(pyname)
        assert np.array_equal(func(), ONES)

    # test nested sample data too
    sample_generator = next(s for s in samples if s.display_name == "Some local ones")
    func = sample_generator.get_callable()
    assert np.array_equal(func(), ONES)


def test_shim_pyname_dock_widget(uses_npe1_plugin):
    """Test that objects defined locally in npe1 hookspecs can be retrieved."""
    mf = _get_mf()
    widgets = mf.contributions.widgets
    assert widgets
    wdg_contrib = next(w for w in widgets if w.display_name == "Local Widget")

    with patch.object(utils, "_import_npe1_shim", wraps=utils._import_npe1_shim) as m:
        caller = wdg_contrib.get_callable()
        assert isinstance(caller, MagicFactory)
        assert "<locals>.local_widget" in caller.keywords["function"].__qualname__
        pyname = "__npe1shim__.npe1_module:napari_experimental_provide_dock_widget_2"
        m.assert_called_once_with(pyname)

        m.reset_mock()
        wdg_contrib2 = next(
            w for w in widgets if w.display_name == "local function" and w.autogenerate
        )
        caller2 = wdg_contrib2.get_callable()
        assert isinstance(caller2, MagicFactory)
        assert "<locals>.local_function" in caller2.keywords["function"].__qualname__
        pyname = "__npe1shim__.npe1_module:napari_experimental_provide_function_1"
        m.assert_called_once_with(pyname)


def test_shim_error_on_import():
    class FakeDist(metadata.Distribution):
        def read_text(self, filename):
            if filename == "METADATA":
                return "Name: fake-plugin\nVersion: 0.1.0\n"

        def locate_file(self, *_):
            ...

    shim = _npe1_adapter.NPE1Adapter(FakeDist())

    def err():
        raise ImportError("No package found.")

    with pytest.warns(UserWarning) as record:
        with patch.object(_npe1_adapter, "manifest_from_npe1", wraps=err):
            shim.contributions
    assert "Error importing contributions for" in str(record[0])
