import shutil
import sys
from importlib import abc, metadata
from pathlib import Path
from unittest.mock import patch

import pytest

from npe2 import PluginManager, PluginManifest
from npe2.manifest import _npe1_adapter

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "sample"


@pytest.fixture
def sample_manifest(sample_path):
    return PluginManifest.from_file(sample_path / "my_plugin" / "napari.yaml")


@pytest.fixture
def compiled_plugin_dir(tmp_path):
    shutil.copytree(FIXTURES / "my-compiled-plugin", tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def uses_sample_plugin(sample_path):
    sys.path.append(str(sample_path))
    try:
        pm = PluginManager.instance()
        pm.discover()
        yield
    finally:
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
def uses_npe1_plugin(npe1_repo):
    import site

    class Importer(abc.MetaPathFinder):
        def find_spec(self, *_, **__):
            return None

        def find_distributions(self, ctx, **k):
            if ctx.name == "npe1-plugin":
                pth = npe1_repo / "npe1-plugin-0.0.1.dist-info"
                yield metadata.PathDistribution(pth)
            return

    sys.meta_path.append(Importer())
    sys.path.append(str(npe1_repo))
    try:
        pkgs = [*site.getsitepackages(), str(npe1_repo)]
        with patch("site.getsitepackages", return_value=pkgs):
            yield
    finally:
        sys.path.remove(str(npe1_repo))


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
    from napari_plugin_engine import PluginManager, napari_hook_specification

    # fmt: off
    class HookSpecs:
        def napari_provide_sample_data(): ...  # type: ignore
        def napari_get_reader(path): ...
        def napari_get_writer(path, layer_types): ...
        def napari_write_graph(path, data, meta): ...
        def napari_write_image(path, data, meta): ...
        def napari_write_labels(path, data, meta): ...
        def napari_write_points(path, data, meta): ...
        def napari_write_shapes(path, data, meta): ...
        def napari_write_surface(path, data, meta): ...
        def napari_write_vectors(path, data, meta): ...
        def napari_experimental_provide_function(): ...  # type: ignore
        def napari_experimental_provide_dock_widget(): ...  # type: ignore
        def napari_experimental_provide_theme(): ...  # type: ignore
    # fmt: on

    for m in dir(HookSpecs):
        if m.startswith("napari"):
            setattr(HookSpecs, m, napari_hook_specification(getattr(HookSpecs, m)))

    pm = PluginManager("napari")
    pm.add_hookspecs(HookSpecs)

    yield pm


@pytest.fixture
def mock_npe1_pm_with_plugin(npe1_repo, npe1_plugin_module):
    """Mocks a fully installed local repository"""
    from npe2._inspection._from_npe1 import plugin_packages

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


@pytest.fixture
def mock_npe1_pm_with_plugin_editable(npe1_repo, npe1_plugin_module, tmp_path):
    """Mocks a fully installed local repository"""
    from npe2._inspection._from_npe1 import plugin_packages

    dist_path = tmp_path / "npe1-plugin-0.0.1.dist-info"
    shutil.copytree(npe1_repo / "npe1-plugin-0.0.1.dist-info", dist_path)

    record_path = dist_path / "RECORD"

    record_content = record_path.read_text().splitlines()
    record_content.pop(-1)
    record_content.append("__editable__.npe1-plugin-0.0.1.pth")

    with record_path.open("w") as f:
        f.write("\n".join(record_content))

    with open(tmp_path / "__editable__.npe1-plugin-0.0.1.pth", "w") as f:
        f.write(str(npe1_repo))

    mock_dist = metadata.PathDistribution(dist_path)

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


@pytest.fixture(autouse=True)
def mock_cache(tmp_path, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(_npe1_adapter, "ADAPTER_CACHE", tmp_path)
        yield tmp_path
