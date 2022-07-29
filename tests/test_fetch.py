import os
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from npe2 import fetch_manifest
from npe2._inspection._fetch import (
    fetch_manifest_with_full_install,
    get_hub_plugin,
    get_hub_plugins,
    get_pypi_plugins,
    get_pypi_url,
)
from npe2.manifest._npe1_adapter import NPE1Adapter


def test_fetch_npe2_manifest():
    mf = fetch_manifest("napari-omero")
    assert mf.name == "napari-omero"
    assert any(mf.contributions.dict().values())
    assert mf.npe1_shim is False


def test_fetch_npe1_manifest_with_writer():
    mf = fetch_manifest("example-plugin")
    assert mf.name == "example-plugin"
    assert mf.contributions.writers
    # Test will eventually fail when example-plugin is updated to npe2
    # This is here as a sentinel
    assert mf.npe1_shim is True


def test_fetch_npe1_manifest_with_sample_data():
    mf = fetch_manifest("napari-pyclesperanto-assistant")
    assert mf.name == "napari-pyclesperanto-assistant"
    assert mf.contributions.sample_data
    # Test will eventually fail when napari-pyclesperanto-assistant is updated to npe2
    # This is here as a sentinel
    assert mf.npe1_shim is True


def test_fetch_npe1_manifest_dock_widget_as_attribute():
    # This tests is just to add coverage of a specific branch of code in the
    # napari_experimental_provide_dock_widget parser, (where the return value
    # is a dotted attribute, rather than a direct name).  I only saw it in
    # brainreg-segment.
    mf = fetch_manifest("brainreg-segment")
    assert mf.name == "brainreg-segment"
    assert mf.contributions.widgets
    # Test will eventually fail when brainreg-segment is updated to npe2
    # This is here as a sentinel
    assert mf.npe1_shim is True


@pytest.mark.parametrize("version", [None, "0.1.0"])
@pytest.mark.parametrize("packagetype", ["sdist", "bdist_wheel", None])
def test_get_pypi_url(version, packagetype):
    assert "npe2" in get_pypi_url("npe2", version=version, packagetype=packagetype)


def test_from_pypi_wheel_bdist_missing():
    error = PackageNotFoundError("No bdist_wheel releases found")
    with patch("npe2._inspection._fetch.get_pypi_url", side_effect=error):
        with pytest.raises(PackageNotFoundError):
            fetch_manifest("my-package")


@pytest.mark.skipif(not os.getenv("CI"), reason="slow, only run on CI")
def testfetch_manifest_with_full_install():
    # TODO: slowest of the tests ... would be nice to provide a local mock
    mf = fetch_manifest_with_full_install("napari-ndtiffs")
    assert isinstance(mf, NPE1Adapter)
    assert mf.name == "napari-ndtiffs"
    assert mf.contributions


def test_get_hub_plugins():
    plugins = get_hub_plugins()
    assert "napari-svg" in plugins


def test_get_hub_plugin():
    info = get_hub_plugin("napari-svg")
    assert info["name"] == "napari-svg"


def test_get_pypi_plugins():
    info = get_pypi_plugins()
    assert "napari-svg" in info
