from pathlib import Path
from unittest.mock import patch

import pytest

from npe2 import PluginManager
from npe2.manifest import _npe1_shim


def test_shim_no_npe1():
    pm = PluginManager()
    pm.discover()
    assert not pm._shims


@pytest.fixture
def mock_cache(tmp_path, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(_npe1_shim, "SHIM_CACHE", tmp_path)
        yield tmp_path


def test_npe1_shim(uses_npe1_plugin, mock_cache: Path):
    """Test that the plugin manager detects npe1 plugins, and can index contribs"""
    pm = PluginManager()
    pm.discover()

    # we've found a shim
    assert len(pm._shims) == 1
    mf = pm.get_manifest("npe1-plugin")
    assert isinstance(mf, _npe1_shim.NPE1Shim)
    assert mf.package_metadata
    assert mf.package_metadata.version == "0.1.0"
    assert mf.package_metadata.name == "npe1-plugin"

    # it's currently unindexed and unstored
    assert not mf._cache_path().exists()
    assert not list(mock_cache.iterdir())

    with patch.object(
        _npe1_shim,
        "manifest_from_npe1",
        wraps=_npe1_shim.manifest_from_npe1,  # type: ignore
    ) as mock:
        pm.index_npe1_shims()
        # the shim has been cleared by the indexing
        assert len(pm._shims) == 0
        # manifest_from_npe1 was called and the result was cached
        mock.assert_called_once_with(mf._dist, shim=True)
        assert mf._cache_path().exists()
        # NOTE: accessing the `.contributions` object would have also triggered
        # importing, like pm.index_npe1_shims() above, but it would not have
        # injected the contributions into the pm._contrib object.
        assert mf.contributions.sample_data

        mock.reset_mock()
        # clear and rediscover... this time we expect the cache to kick in
        pm.discover(clear=True)
        assert len(pm._shims) == 1
        pm.index_npe1_shims()
        assert len(pm._shims) == 0
        mock.assert_not_called()


def test_npe1_shim_cache(uses_npe1_plugin, mock_cache: Path):
    """Test that we can clear cache, etc.."""
    pm = PluginManager()
    pm.discover()

    with patch.object(
        _npe1_shim,
        "manifest_from_npe1",
        wraps=_npe1_shim.manifest_from_npe1,  # type: ignore
    ) as mock:

        # if we clear the cache, it should import again
        mf = pm.get_manifest("npe1-plugin")
        assert isinstance(mf, _npe1_shim.NPE1Shim)
        pm.index_npe1_shims()
        mock.assert_called_once_with(mf._dist, shim=True)
        assert mf._cache_path().exists()

        _npe1_shim.clear_cache()
        assert not mf._cache_path().exists()

        mock.reset_mock()
        pm.discover(clear=True)
        pm.index_npe1_shims()
        mf = pm.get_manifest("npe1-plugin")
        assert isinstance(mf, _npe1_shim.NPE1Shim)
        mock.assert_called_once_with(mf._dist, shim=True)
        assert mf._cache_path().exists()
        _npe1_shim.clear_cache(names=["not-our-plugin"])
        assert mf._cache_path().exists()
        _npe1_shim.clear_cache(names=["npe1-plugin"])
        assert not mf._cache_path().exists()
