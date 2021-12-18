from pathlib import Path
from unittest.mock import patch

import pytest

from npe2._from_npe1 import (
    HookSpecs,
    convert_repository,
    get_top_module_path,
    manifest_from_npe1,
)

try:
    from importlib.metadata import PackageNotFoundError
except ImportError:
    from importlib_metadata import PackageNotFoundError  # type: ignore

NPE1_REPO = Path(__file__).parent / "npe1-plugin"


@pytest.fixture
def npe1_plugin_module():
    import sys
    from importlib.util import module_from_spec, spec_from_file_location

    npe1_module_path = NPE1_REPO / "npe1_module" / "__init__.py"
    spec = spec_from_file_location("npe1_module", npe1_module_path)
    assert spec
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore
    try:
        yield module
    finally:
        del sys.modules[spec.name]


@pytest.fixture
def mock_npe1_pm():
    from napari_plugin_engine import PluginManager

    pm = PluginManager("napari")
    pm.add_hookspecs(HookSpecs)

    with patch("npe2._from_npe1.npe1_plugin_manager", new=lambda: (pm, (1, []))):
        yield pm


@pytest.fixture
def mock_npe1_pm_with_plugin(mock_npe1_pm):
    """Mocks a fully installed local repository"""
    from npe2._from_npe1 import metadata, plugin_packages

    mock_npe1_pm.register(npe1_plugin_module, "npe1-plugin")
    mock_dist = metadata.PathDistribution(NPE1_REPO / "npe1-plugin-0.0.1.dist-info")

    def _dists():
        return [mock_dist]

    def _from_name(name):
        if name == "npe1-plugin":
            return mock_dist
        raise metadata.PackageNotFoundError(name)

    setup_cfg = NPE1_REPO / "setup.cfg"
    new_manifest = NPE1_REPO / "npe1_module" / "napari.yaml"
    with (
        patch.object(metadata, "distributions", new=_dists),
        patch.object(metadata.Distribution, "from_name", new=_from_name),
    ):
        cfg = setup_cfg.read_text()
        plugin_packages.cache_clear()
        try:
            yield mock_npe1_pm
        finally:
            plugin_packages.cache_clear()
            setup_cfg.write_text(cfg)
            if new_manifest.exists():
                new_manifest.unlink()
            if (NPE1_REPO / "setup.py").exists():
                (NPE1_REPO / "setup.py").unlink()


@pytest.mark.filterwarnings("ignore:Failed to convert napari_get_writer")
@pytest.mark.parametrize("package", ["svg", "napari-animation"])
def test_conversion(package):
    assert manifest_from_npe1(package)


def test_conversion_from_module(mock_npe1_pm, npe1_plugin_module):
    mf = manifest_from_npe1(module=npe1_plugin_module)
    assert isinstance(mf.dict(), dict)


def test_conversion_from_package(mock_npe1_pm_with_plugin):
    setup_cfg = NPE1_REPO / "setup.cfg"
    before = setup_cfg.read_text()
    convert_repository(NPE1_REPO, dry_run=True)
    assert setup_cfg.read_text() == before
    assert not (NPE1_REPO / "npe1_module" / "napari.yaml").exists()
    convert_repository(NPE1_REPO, dry_run=False)
    new_setup = setup_cfg.read_text()
    assert new_setup != before
    assert (
        "[options.entry_points]\n"
        "napari.manifest = \n	npe1-plugin = npe1_module:napari.yaml"
    ) in new_setup
    assert "[options.package_data]\nnpe1_module = napari.yaml" in new_setup
    assert (NPE1_REPO / "npe1_module" / "napari.yaml").is_file()

    with pytest.raises(ValueError) as e:
        convert_repository(NPE1_REPO)
    assert "Is this package already converted?" in str(e.value)


def test_conversion_from_package_setup_py(mock_npe1_pm_with_plugin):
    (NPE1_REPO / "setup.cfg").unlink()
    (NPE1_REPO / "setup.py").write_text(
        """from setuptools import setup

setup(
    name='npe1-plugin',
    entry_points={"napari.plugin": ["npe1-plugin = npe1_module"]}
)
"""
    )
    with pytest.warns(UserWarning) as record:
        convert_repository(NPE1_REPO)
    msg = record[0].message
    assert "Cannot auto-update setup.py, please edit setup.py as follows" in str(msg)
    assert "npe1-plugin = npe1_module:napari.yaml" in str(msg)


def test_conversion_missing():
    with pytest.raises(ModuleNotFoundError), pytest.warns(UserWarning):
        manifest_from_npe1("does-not-exist-asdf6as987")


def test_conversion_package_is_not_a_plugin():
    with pytest.raises(PackageNotFoundError):
        manifest_from_npe1("pytest")


def test_convert_repo():
    convert_repository


def test_get_top_module_path(mock_npe1_pm_with_plugin):
    get_top_module_path("npe1-plugin")
