from importlib import metadata
from pathlib import Path
from unittest.mock import patch

import pytest

from npe2 import PluginManifest
from npe2._pydantic_compat import ValidationError
from npe2.manifest import PackageMetadata
from npe2.manifest.schema import ENTRY_POINT

SAMPLE_PLUGIN_NAME = "my-plugin"
SAMPLE_MODULE_NAME = "my_plugin"


def test_sample_plugin_valid(sample_manifest):
    assert sample_manifest


def test_discover_empty():
    # sanity check to make sure sample_plugin must be in path to be discovered
    results = PluginManifest.discover()
    manifests = [result.manifest.name for result in results if result.manifest]
    assert SAMPLE_PLUGIN_NAME not in manifests


def test_schema():
    assert isinstance(PluginManifest.schema_json(), str)

    dschema = PluginManifest.schema()
    assert isinstance(dschema, dict)
    assert "name" in dschema["properties"]


def test_discover(uses_sample_plugin):
    discover_results = list(PluginManifest.discover())
    assert len(discover_results) == 1
    [(manifest, distribution, error)] = discover_results
    assert manifest and manifest.name == SAMPLE_PLUGIN_NAME
    assert distribution
    entrypoint = next(iter(distribution.entry_points))
    assert entrypoint and entrypoint.group == "napari.manifest" == ENTRY_POINT
    assert entrypoint.value == f"{SAMPLE_MODULE_NAME}:napari.yaml"
    assert error is None


def test_discover_errors(tmp_path: Path):
    """testing various discovery errors"""
    # package with proper `napari.manifest` entry_point, but invalid pointer to
    # a manifest should yield an error in results
    a = tmp_path / "a"
    a.mkdir()
    a_ep = a / "entry_points.txt"
    bad_value = "asdfsad:blahblahblah.yaml"
    a_ep.write_text(f"[napari.manifest]\n{SAMPLE_PLUGIN_NAME} = {bad_value}")

    # package with proper `napari.manifest` entry_point, but invalid manifest
    b = tmp_path / "b"
    b.mkdir()
    b_ep = b / "entry_points.txt"
    b_ep.write_text("[napari.manifest]\nsome_plugin = module:napari.yaml")
    module = tmp_path / "module"
    module.mkdir()
    (module / "napari.yaml").write_text("name: hi??")

    # a regular package, with out napari.manifest entry_point should just be skipped
    c = tmp_path / "c"
    c.mkdir()
    c_ep = c / "entry_points.txt"
    c_ep.write_text("[console.scripts]\nsomething = something")

    dists = [
        metadata.PathDistribution(a),
        metadata.PathDistribution(b),
        metadata.PathDistribution(c),
    ]

    with patch.object(metadata, "distributions", return_value=dists):
        discover_results = list(PluginManifest.discover(paths=[tmp_path]))

    assert len(discover_results) == 2
    res_a, res_b = discover_results
    assert res_a.manifest is None
    assert res_a.distribution
    assert next(iter(res_a.distribution.entry_points)).value == bad_value
    assert "Cannot find module 'asdfsad'" in str(res_a.error)

    assert res_b.manifest is None
    assert res_b.distribution
    assert next(iter(res_b.distribution.entry_points)).value == "module:napari.yaml"
    assert isinstance(res_b.error, ValidationError)


def test_package_meta(uses_sample_plugin):
    direct_meta = PackageMetadata.for_package(SAMPLE_PLUGIN_NAME)
    assert direct_meta.name == SAMPLE_PLUGIN_NAME
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
    for d in metadata.distributions():
        assert PackageMetadata.from_dist_metadata(d.metadata)


@pytest.mark.parametrize("format", ["toml", "json", "yaml", "pyproject"])
def test_export_round_trip(sample_manifest, tmp_path, format):
    """Test that an exported manifest can be round-tripped."""
    if format == "pyproject":
        out_file = tmp_path / "pyproject.toml"
        out_file.write_text(sample_manifest.toml(pyproject=True))
    else:
        out_file = tmp_path / f"napari.{format}"
        out_file.write_text(getattr(sample_manifest, format)())
    assert sample_manifest == PluginManifest.from_file(out_file)


def test_from_distribution(uses_sample_plugin):
    mf = PluginManifest.from_distribution(SAMPLE_PLUGIN_NAME)
    assert mf.name == SAMPLE_PLUGIN_NAME
    assert mf.package_metadata == PackageMetadata.for_package(SAMPLE_PLUGIN_NAME)

    with pytest.raises(metadata.PackageNotFoundError):
        _ = PluginManifest.from_distribution("not-an-installed-package")

    with pytest.raises(ValueError) as e:
        # valid package, but doesn't have a manifest
        _ = PluginManifest.from_distribution("pytest")
    assert "exists but does not provide a napari manifest" in str(e.value)


def test_from_package_name_err():
    with pytest.raises(ValueError) as e:
        PluginManifest._from_package_or_name("nonsense")
    assert "Could not find manifest for 'nonsense'" in str(e.value)


def test_dotted_name_with_command():
    with pytest.raises(ValidationError, match="must start with the current package"):
        PluginManifest(
            name="plugin.plugin-sample",
            contributions={"commands": [{"id": "plugin.command", "title": "Sample"}]},
        )
    with pytest.raises(ValidationError, match="must begin with the package name"):
        PluginManifest(
            name="plugin.plugin-sample",
            contributions={
                "commands": [{"id": "plugin.plugin-samplecommand", "title": "Sample"}]
            },
        )

    PluginManifest(
        name="plugin.plugin-sample",
        contributions={
            "commands": [{"id": "plugin.plugin-sample.command", "title": "Sample"}]
        },
    )


def test_visibility():
    mf = PluginManifest(name="myplugin")
    assert mf.is_visible

    mf = PluginManifest(name="myplugin", visibility="hidden")
    assert not mf.is_visible

    with pytest.raises(ValidationError):
        mf = PluginManifest(name="myplugin", visibility="other")


def test_icon():
    PluginManifest(name="myplugin", icon="my_plugin:myicon.png")


def test_dotted_plugin_name():
    """Test that"""
    name = "some.namespaced.plugin"
    cmd_id = f"{name}.frame_rate_widget"
    mf = PluginManifest(
        name=name,
        contributions={
            "commands": [
                {
                    "id": cmd_id,
                    "title": "open my widget",
                }
            ],
            "widgets": [
                {
                    "command": cmd_id,
                    "display_name": "Plot frame rate",
                }
            ],
        },
    )
    assert mf.contributions.widgets
    assert mf.contributions.widgets[0].plugin_name == name
