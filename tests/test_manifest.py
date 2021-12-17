from npe2 import PluginManifest
from npe2.manifest.package_metadata import PackageMetadata


def test_sample_plugin_valid(sample_path):
    assert PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path to be discovered
    manifests = [
        result.manifest.name for result in PluginManifest.discover() if result.manifest
    ]
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


def test_toml_round_trip(sample_path, tmp_path):
    pm = PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")

    toml_file = tmp_path / "napari.toml"
    toml_file.write_text(pm.toml())

    pm2 = PluginManifest.from_file(toml_file)
    assert pm == pm2


def test_json_round_trip(sample_path, tmp_path):
    pm = PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")

    json_file = tmp_path / "napari.json"
    json_file.write_text(pm.json())

    pm2 = PluginManifest.from_file(json_file)
    assert pm == pm2
