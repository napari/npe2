import os
import urllib.request
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from npe2 import PluginManifest, fetch_manifest
from npe2._inspection._fetch import (
    _manifest_from_pypi_sdist,
    get_hub_plugin,
    get_manifest_from_wheel,
    get_pypi_plugins,
    get_pypi_url,
)


def test_fetch_npe2_manifest():
    mf = fetch_manifest("napari-omero")
    assert mf.name == "napari-omero"
    assert any(mf.contributions.dict().values())
    assert mf.npe1_shim is False


@pytest.mark.skip("package looks deleted from pypi")
def test_fetch_npe1_manifest_with_writer():
    mf = fetch_manifest("dummy-test-plugin", version="0.1.3")
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
    mf = fetch_manifest("brainreg-segment", version="0.2.18")
    assert mf.name == "brainreg-segment"
    assert mf.contributions.widgets
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
def test_manifest_from_sdist():
    mf = _manifest_from_pypi_sdist("zarpaint")
    assert mf.name == "zarpaint"


def test_get_manifest_from_wheel(tmp_path):
    url = "https://files.pythonhosted.org/packages/f0/cc/7f6fbce81be3eb73266f398e49df92859ba247134eb086704dd70b43819a/affinder-0.2.3-py3-none-any.whl"  # noqa
    dest = tmp_path / "affinder-0.2.3-py3-none-any.whl"
    urllib.request.urlretrieve(url, dest)
    mf = get_manifest_from_wheel(dest)
    assert mf.name == "affinder"


def test_get_hub_plugin():
    info = get_hub_plugin("napari-svg")
    assert info["name"] == "napari-svg"


def test_get_pypi_plugins():
    plugins = get_pypi_plugins()
    assert len(plugins) > 0


@pytest.mark.skipif(not os.getenv("CI"), reason="slow, only run on CI")
@pytest.mark.parametrize(
    "url",
    [
        "https://files.pythonhosted.org/packages/fb/01/e59bc1d6ac96f84ce9d7a46cc5422250e047958ead6c5693ed386cf94003/napari_dv-0.3.0.tar.gz",  # noqa
        "https://files.pythonhosted.org/packages/5d/ae/17779e12ce60d8329306963e1a8dec608465caee582440011ff0c1310715/example_plugin-0.0.7-py3-none-any.whl",  # noqa
        "git+https://github.com/napari/dummy-test-plugin.git@npe1",
        # this one doesn't use setuptools_scm, can check direct zip without clone
        "https://github.com/jo-mueller/napari-stl-exporter/archive/refs/heads/main.zip",
    ],
)
def test_fetch_urls(url):
    assert isinstance(fetch_manifest(url), PluginManifest)
