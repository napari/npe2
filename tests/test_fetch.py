import os
import urllib.request
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from npe2 import PluginManifest, fetch_manifest
from npe2._inspection._fetch import (
    _get_manifest_from_zip_url,
    _manifest_from_pypi_sdist,
    get_hub_plugin,
    get_manifest_from_wheel,
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
    mf = fetch_manifest("napari-kics")
    assert mf.name == "napari-kics"
    assert mf.contributions.sample_data
    # Test will eventually fail when napari-kics is updated to npe2
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
    url = "https://files.pythonhosted.org/packages/f0/cc/7f6fbce81be3eb73266f398e49df92859ba247134eb086704dd70b43819a/affinder-0.2.3-py3-none-any.whl"
    dest = tmp_path / "affinder-0.2.3-py3-none-any.whl"
    urllib.request.urlretrieve(url, dest)
    mf = get_manifest_from_wheel(dest)
    assert mf.name == "affinder"


def test_get_hub_plugin():
    info = get_hub_plugin("napari-svg")
    assert info["name"] == "napari-svg"


@pytest.mark.skipif(not os.getenv("CI"), reason="slow, only run on CI")
@pytest.mark.parametrize(
    "url",
    [
        "https://files.pythonhosted.org/packages/fb/01/e59bc1d6ac96f84ce9d7a46cc5422250e047958ead6c5693ed386cf94003/napari_dv-0.3.0.tar.gz",
        "https://files.pythonhosted.org/packages/5d/ae/17779e12ce60d8329306963e1a8dec608465caee582440011ff0c1310715/example_plugin-0.0.7-py3-none-any.whl",
        "git+https://github.com/napari/dummy-test-plugin.git@npe1",
        # this one doesn't use setuptools_scm, can check direct zip without clone
        "https://github.com/jo-mueller/napari-stl-exporter/archive/refs/heads/main.zip",
    ],
)
def test_fetch_urls(url):
    assert isinstance(fetch_manifest(url), PluginManifest)


def test_get_manifest_from_zip_url(tmp_path, monkeypatch):
    # Mock the _tmp_zip_download context manager
    mock_zip_path = tmp_path / "extracted"
    mock_zip_path.mkdir()

    # Create a mock source directory inside the extracted zip
    src_dir = mock_zip_path / "plugin-source-1.0"
    src_dir.mkdir()

    # Mock the _build_src_and_extract_manifest to return a test manifest
    test_manifest = PluginManifest(name="test-plugin")

    def mock_build_src_and_extract_manifest(src_dir):
        return test_manifest

    from contextlib import contextmanager

    @contextmanager
    def mock_tmp_zip_download(url):
        yield mock_zip_path

    monkeypatch.setattr(
        "npe2._inspection._fetch._tmp_zip_download", mock_tmp_zip_download
    )
    monkeypatch.setattr(
        "npe2._inspection._fetch._build_src_and_extract_manifest",
        mock_build_src_and_extract_manifest,
    )

    # Test the function
    result = _get_manifest_from_zip_url("https://example.com/plugin.zip")

    # Verify the result
    assert result == test_manifest
    assert result.name == "test-plugin"


def test_get_manifest_from_zip_url_with_pyproject_toml_tomllib(tmp_path, monkeypatch):
    # Test pyproject.toml with napari config using tomllib
    mock_zip_path = tmp_path / "extracted"
    mock_zip_path.mkdir()

    # Create pyproject.toml with napari config
    pyproject_content = b"""
[tool.napari]
name = "test-plugin"
"""
    pyproject_path = mock_zip_path / "pyproject.toml"
    pyproject_path.write_bytes(pyproject_content)

    from contextlib import contextmanager

    @contextmanager
    def mock_tmp_zip_download(url):
        yield mock_zip_path

    monkeypatch.setattr(
        "npe2._inspection._fetch._tmp_zip_download", mock_tmp_zip_download
    )

    # Mock PluginManifest.from_file to return a test manifest
    test_manifest = PluginManifest(name="test-plugin")
    monkeypatch.setattr(
        "npe2.manifest.PluginManifest.from_file", lambda path: test_manifest
    )

    # Test the function
    result = _get_manifest_from_zip_url("https://example.com/plugin.zip")

    # Verify the result
    assert result == test_manifest
    assert result.name == "test-plugin"


def test_get_manifest_from_zip_url_with_pyproject_toml_tomli(tmp_path, monkeypatch):
    # Test pyproject.toml with napari config using tomli fallback
    mock_zip_path = tmp_path / "extracted"
    mock_zip_path.mkdir()

    # Create pyproject.toml with napari config
    pyproject_content = b"""
[tool.napari]
name = "test-plugin"
"""
    pyproject_path = mock_zip_path / "pyproject.toml"
    pyproject_path.write_bytes(pyproject_content)

    from contextlib import contextmanager

    @contextmanager
    def mock_tmp_zip_download(url):
        yield mock_zip_path

    monkeypatch.setattr(
        "npe2._inspection._fetch._tmp_zip_download", mock_tmp_zip_download
    )

    # Mock PluginManifest.from_file to return a test manifest
    test_manifest = PluginManifest(name="test-plugin")
    monkeypatch.setattr(
        "npe2.manifest.PluginManifest.from_file", lambda path: test_manifest
    )

    # Mock tomllib to not exist, forcing tomli fallback
    import sys

    original_modules = sys.modules.copy()
    if "tomllib" in sys.modules:
        del sys.modules["tomllib"]

    try:
        # Test the function
        result = _get_manifest_from_zip_url("https://example.com/plugin.zip")

        # Verify the result
        assert result == test_manifest
        assert result.name == "test-plugin"
    finally:
        # Restore modules
        sys.modules.update(original_modules)


def test_get_manifest_from_zip_url_with_pyproject_toml_no_napari(tmp_path, monkeypatch):
    # Test pyproject.toml without napari config
    mock_zip_path = tmp_path / "extracted"
    mock_zip_path.mkdir()

    # Create pyproject.toml without napari config
    pyproject_content = b"""
[tool.other]
name = "other-tool"
"""
    pyproject_path = mock_zip_path / "pyproject.toml"
    pyproject_path.write_bytes(pyproject_content)

    # Create a mock source directory for fallback
    src_dir = mock_zip_path / "plugin-source"
    src_dir.mkdir()

    from contextlib import contextmanager

    @contextmanager
    def mock_tmp_zip_download(url):
        yield mock_zip_path

    monkeypatch.setattr(
        "npe2._inspection._fetch._tmp_zip_download", mock_tmp_zip_download
    )

    # Mock the fallback to build from source
    test_manifest = PluginManifest(name="test-plugin")
    monkeypatch.setattr(
        "npe2._inspection._fetch._build_src_and_extract_manifest",
        lambda src_dir: test_manifest,
    )

    # Test the function
    result = _get_manifest_from_zip_url("https://example.com/plugin.zip")

    # Verify the result (should use fallback since no napari config)
    assert result == test_manifest
    assert result.name == "test-plugin"


def test_pyproject_toml_napari_section_coverage(tmp_path, monkeypatch):
    # Direct test of the find_manifest_file function to ensure coverage
    from npe2._inspection._fetch import _get_manifest_from_zip_url

    mock_zip_path = tmp_path / "extracted"
    mock_zip_path.mkdir()

    # Create nested directory structure
    nested_dir = mock_zip_path / "plugin" / "src"
    nested_dir.mkdir(parents=True)

    # Create pyproject.toml with napari config in nested dir
    pyproject_content = b"""
[tool.napari]
name = "test-plugin"
display_name = "Test Plugin"
"""
    pyproject_path = nested_dir / "pyproject.toml"
    pyproject_path.write_bytes(pyproject_content)

    # Create a napari.yaml manifest
    manifest_content = """
name: test-plugin
display_name: Test Plugin
"""
    manifest_path = nested_dir / "napari.yaml"
    manifest_path.write_text(manifest_content)

    from contextlib import contextmanager

    @contextmanager
    def mock_tmp_zip_download(url):
        yield mock_zip_path

    monkeypatch.setattr(
        "npe2._inspection._fetch._tmp_zip_download", mock_tmp_zip_download
    )

    # Test the function - it should find the napari.yaml first
    result = _get_manifest_from_zip_url("https://example.com/plugin.zip")
    assert result.name == "test-plugin"
