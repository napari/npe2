import shutil
from pathlib import Path

import pytest

from npe2.implements import compile
from npe2.manifest.schema import PluginManifest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def compiled_plugin_dir(tmp_path):
    shutil.copytree(FIXTURES / "my-compiled-plugin", tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_compile(compiled_plugin_dir: Path, tmp_path: Path):
    """
    Test that the plugin manager can be compiled.
    """
    with pytest.raises(ValueError, match='must have an extension of .json, .yaml, or'):
        compile(compiled_plugin_dir, 'bad_path')

    dest = tmp_path / "output.yaml"
    mf = compile(compiled_plugin_dir, dest=dest)
    assert isinstance(mf, PluginManifest)
    assert mf.name == "my-compiled-plugin"
    assert mf.contributions.commands and len(mf.contributions.commands) == 5
    assert dest.exists()
    assert PluginManifest.from_file(dest) == mf
