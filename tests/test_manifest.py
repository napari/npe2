import pytest

from npe2 import PluginManifest
from npe2.manifest.package_metadata import PackageMetadata


def test_sample_plugin_valid(sample_manifest):
    assert sample_manifest


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path to be discovered
    results = PluginManifest.discover()
    manifests = [result.manifest.name for result in results if result.manifest]
    assert "my_plugin" not in manifests


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover(uses_sample_plugin):
    discover_results = list(PluginManifest.discover())
    assert len(discover_results) == 1
    [(manifest, entrypoint, error)] = discover_results
    assert manifest and manifest.name == "my_plugin"
    assert entrypoint and entrypoint.group == "napari.manifest"
    assert entrypoint.value == "my_plugin:napari.yaml"
    assert error is None


def test_package_meta(uses_sample_plugin):
    direct_meta = PackageMetadata.for_package("my_plugin")
    assert direct_meta.name == "my_plugin"
    assert direct_meta.version == "1.2.3"
    discover_results = list(PluginManifest.discover())
    [(manifest, *_)] = discover_results
    assert manifest
    assert manifest.package_metadata == direct_meta

    assert manifest.author == direct_meta.author == "The Black Knight"
    assert manifest.description == direct_meta.summary == "My napari plugin"
    assert manifest.package_version == direct_meta.version == "1.2.3"
    assert manifest.license == direct_meta.license == "BSD-3"


def test_all_package_meta():
    """make sure PackageMetadata works for whatever packages are in the environment.

    just a brute force way to get a little more validation coverage
    """
    try:
        from importlib.metadata import distributions
    except ImportError:
        from importlib_metadata import distributions  # type: ignore

    for d in distributions():
        assert PackageMetadata.from_dist_metadata(d.metadata)


@pytest.mark.parametrize("format", ["toml", "json", "yaml"])
def test_export_round_trip(sample_manifest, tmp_path, format):
    """Test that an exported manifest can be round-tripped."""
    out_file = tmp_path / f"napari.{format}"
    out_file.write_text(getattr(sample_manifest, format)())
    assert sample_manifest == PluginManifest.from_file(out_file)
