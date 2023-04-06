from functools import partial
from importlib import metadata
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from npe2 import PluginManager
from npe2.manifest import _npe1_adapter, utils
from npe2.manifest.contributions import SampleDataGenerator
from npe2.manifest.utils import SHIM_NAME_PREFIX


def test_adapter_no_npe1():
    pm = PluginManager()
    pm.discover()
    assert not pm._npe1_adapters


def test_npe1_adapter(uses_npe1_plugin, mock_cache: Path):
    """Test that the plugin manager detects npe1 plugins, and can index contribs"""
    pm = PluginManager()
    pm.discover(include_npe1=True)

    # we've found an adapter
    assert len(pm._npe1_adapters) == 1
    mf = pm.get_manifest("npe1-plugin")
    assert isinstance(mf, _npe1_adapter.NPE1Adapter)
    assert mf.package_metadata
    assert mf.package_metadata.version == "0.1.0"
    assert mf.package_metadata.name == "npe1-plugin"

    # it's currently unindexed and unstored
    assert not mf._cache_path().exists()
    assert not list(mock_cache.iterdir())

    with patch.object(
        _npe1_adapter,
        "manifest_from_npe1",
        wraps=_npe1_adapter.manifest_from_npe1,  # type: ignore
    ) as mock:
        pm.index_npe1_adapters()
        # the adapter has been cleared by the indexing
        assert len(pm._npe1_adapters) == 0
        # manifest_from_npe1 was called
        mock.assert_called_once_with(mf._dist, adapter=True)
        assert mf._cache_path().exists()
        # NOTE: accessing the `.contributions` object would have also triggered
        # importing, like pm.index_npe1_adapters() above, but it would not have
        # injected the contributions into the pm._contrib object.
        assert mf.contributions.sample_data

        mock.reset_mock()
        # clear and rediscover... this time we expect the cache to kick in
        pm.discover(clear=True, include_npe1=True)
        assert len(pm._npe1_adapters) == 1
        pm.index_npe1_adapters()
        assert len(pm._npe1_adapters) == 0
        mock.assert_not_called()


def test_npe1_adapter_cache(uses_npe1_plugin, mock_cache: Path):
    """Test that we can clear cache, etc.."""
    pm = PluginManager()
    pm.discover(include_npe1=True)

    with patch.object(
        _npe1_adapter,
        "manifest_from_npe1",
        wraps=_npe1_adapter.manifest_from_npe1,  # type: ignore
    ) as mock:
        # if we clear the cache, it should import again
        mf = pm.get_manifest("npe1-plugin")
        assert isinstance(mf, _npe1_adapter.NPE1Adapter)
        pm.index_npe1_adapters()
        mock.assert_called_once_with(mf._dist, adapter=True)
        assert mf._cache_path().exists()

        _npe1_adapter.clear_cache()
        assert not mf._cache_path().exists()

        mock.reset_mock()
        pm.discover(clear=True, include_npe1=True)
        pm.index_npe1_adapters()
        mf = pm.get_manifest("npe1-plugin")
        assert isinstance(mf, _npe1_adapter.NPE1Adapter)
        mock.assert_called_once_with(mf._dist, adapter=True)
        assert mf._cache_path().exists()
        _npe1_adapter.clear_cache(names=["not-our-plugin"])
        assert mf._cache_path().exists()
        _npe1_adapter.clear_cache(names=["npe1-plugin"])
        assert not mf._cache_path().exists()


def _get_mf() -> _npe1_adapter.NPE1Adapter:
    pm = PluginManager.instance()
    pm.discover(include_npe1=True)
    pm.index_npe1_adapters()
    mf = pm.get_manifest("npe1-plugin")
    assert isinstance(mf, _npe1_adapter.NPE1Adapter)
    return mf


def test_adapter_pyname_sample_data(uses_npe1_plugin, mock_cache):
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
        pyname = f"{SHIM_NAME_PREFIX}npe1_module:napari_provide_sample_data_1"
        m.assert_called_once_with(pyname)
        assert np.array_equal(func(), ONES)

    # test nested sample data too
    sample_generator = next(s for s in samples if s.display_name == "Some local ones")
    func = sample_generator.get_callable()
    assert np.array_equal(func(), ONES)


def test_adapter_pyname_dock_widget(uses_npe1_plugin, mock_cache):
    """Test that objects defined locally in npe1 hookspecs can be retrieved."""
    mf = _get_mf()
    widgets = mf.contributions.widgets
    assert widgets
    wdg_contrib = next(w for w in widgets if w.display_name == "Local Widget")

    with patch.object(utils, "_import_npe1_shim", wraps=utils._import_npe1_shim) as m:
        caller = wdg_contrib.get_callable()
        assert isinstance(caller, partial)
        assert "<locals>.local_widget" in caller.keywords["function"].__qualname__
        pyname = (
            f"{SHIM_NAME_PREFIX}npe1_module:napari_experimental_provide_dock_widget_2"
        )
        m.assert_called_once_with(pyname)

        m.reset_mock()
        wdg_contrib2 = next(
            w for w in widgets if w.display_name == "local function" and w.autogenerate
        )
        caller2 = wdg_contrib2.get_callable()
        assert isinstance(caller2, partial)
        assert "<locals>.local_function" in caller2.keywords["function"].__qualname__
        pyname = f"{SHIM_NAME_PREFIX}npe1_module:napari_experimental_provide_function_1"
        m.assert_called_once_with(pyname)


def test_adapter_error_on_import():
    class FakeDist(metadata.Distribution):
        def read_text(self, filename):
            if filename == "METADATA":
                return "Name: fake-plugin\nVersion: 0.1.0\n"

        def locate_file(self, *_):
            ...

    adapter = _npe1_adapter.NPE1Adapter(FakeDist())

    def err():
        raise ImportError("No package found.")

    with pytest.warns(UserWarning) as record:
        with patch.object(_npe1_adapter, "manifest_from_npe1", wraps=err):
            _ = adapter.contributions
    assert "Error importing contributions for" in str(record[0])


def test_adapter_cache_fail(uses_npe1_plugin, mock_cache):
    pm = PluginManager()
    pm.discover(include_npe1=True)
    mf = pm.get_manifest("npe1-plugin")

    def err(obj):
        raise OSError("Can't cache")

    with patch.object(_npe1_adapter.NPE1Adapter, "_save_to_cache", err):
        # shouldn't reraise the error
        _ = mf.contributions
