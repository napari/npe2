import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from npe2 import PluginManager, PluginManifest


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "sample"


@pytest.fixture
def sample_manifest(sample_path):
    return PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")


@pytest.fixture
def uses_sample_plugin(sample_path):
    sys.path.append(str(sample_path))
    pm = PluginManager.instance()
    pm.discover()
    yield
    sys.path.remove(str(sample_path))


@pytest.fixture
def plugin_manager():
    pm = PluginManager()
    pm.discover()
    return pm


@pytest.fixture(autouse=True)
def mock_discover():
    _discover = PluginManifest.discover

    def wrapper(*args, **kwargs):
        before = sys.path.copy()
        # only allowing things from test directory in discover
        sys.path = [x for x in sys.path if str(Path(__file__).parent) in x]
        try:
            yield from _discover(*args, **kwargs)
        finally:
            sys.path = before

    with patch("npe2.PluginManifest.discover", wraps=wrapper):
        yield 1


@pytest.fixture
def npe1_repo():
    return Path(__file__).parent / "npe1-plugin"


@pytest.fixture
def npe1_plugin_module(npe1_repo):
    import sys
    from importlib.util import module_from_spec, spec_from_file_location

    npe1_module_path = npe1_repo / "npe1_module" / "__init__.py"
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

    from npe2._from_npe1 import HookSpecs

    pm = PluginManager("napari")
    pm.add_hookspecs(HookSpecs)

    with patch("npe2._from_npe1.npe1_plugin_manager", new=lambda: (pm, (1, []))):
        yield pm


@pytest.fixture
def mock_npe1_pm_with_plugin(npe1_repo, mock_npe1_pm, npe1_plugin_module):
    """Mocks a fully installed local repository"""
    from npe2._from_npe1 import metadata, plugin_packages

    mock_npe1_pm.register(npe1_plugin_module, "npe1-plugin")
    mock_dist = metadata.PathDistribution(npe1_repo / "npe1-plugin-0.0.1.dist-info")

    def _dists():
        return [mock_dist]

    def _from_name(name):
        if name == "npe1-plugin":
            return mock_dist
        raise metadata.PackageNotFoundError(name)

    setup_cfg = npe1_repo / "setup.cfg"
    new_manifest = npe1_repo / "npe1_module" / "napari.yaml"
    with patch.object(metadata, "distributions", new=_dists):
        with patch.object(metadata.Distribution, "from_name", new=_from_name):
            cfg = setup_cfg.read_text()
            plugin_packages.cache_clear()
            try:
                yield mock_npe1_pm
            finally:
                plugin_packages.cache_clear()
                setup_cfg.write_text(cfg)
                if new_manifest.exists():
                    new_manifest.unlink()
                if (npe1_repo / "setup.py").exists():
                    (npe1_repo / "setup.py").unlink()
