import os
from unittest.mock import patch

import pytest

from npe2 import fetch_manifest
from npe2._fetch import (
    _fetch_manifest_with_full_install,
    get_hub_plugin,
    get_hub_plugins,
    get_pypi_url,
)
from npe2.manifest._npe1_adapter import NPE1Adapter


def test_npe2_from_pypi_wheel():
    mf = fetch_manifest("napari-omero")
    assert mf.name == "napari-omero"
    assert mf.contributions


@pytest.mark.parametrize("version", [None, "0.1.0"])
@pytest.mark.parametrize("packagetype", ["sdist", "bdist_wheel", None])
def test_get_pypi_url(version, packagetype):
    assert "npe2" in get_pypi_url("npe2", version=version, packagetype=packagetype)


def test_from_pypi_wheel_bdist_missing():
    error = KeyError("No bdist_wheel releases found")
    p2 = patch("npe2._fetch.get_pypi_url", side_effect=error)
    with patch("npe2._fetch._fetch_manifest_with_full_install") as mock_fetch, p2:
        fetch_manifest("my-package")
    mock_fetch.assert_called_once_with("my-package", version=None)


@pytest.mark.skipif(not os.getenv("CI"), reason="slow, only run on CI")
def test_fetch_manifest_with_full_install():
    # TODO: slowest of the tests ... would be nice to provide a local mock
    mf = _fetch_manifest_with_full_install("napari-ndtiffs")
    assert isinstance(mf, NPE1Adapter)
    assert mf.name == "napari-ndtiffs"
    assert mf.contributions


def test_get_hub_plugins():
    plugins = get_hub_plugins()
    assert "napari-svg" in plugins


def test_get_hub_plugin():
    info = get_hub_plugin("napari-svg")
    assert info["name"] == "napari-svg"
