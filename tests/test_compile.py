from npe2.implements import compile
import pytest
from pathlib import Path
import shutil

from npe2.manifest.schema import PluginManifest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def compiled_plugin_dir(tmp_path):
    shutil.copytree(FIXTURES / "my-compiled-plugin", tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_compile(compiled_plugin_dir):
    """
    Test that the plugin manager can be compiled.
    """
    mf = compile(compiled_plugin_dir, plugin_name="my-compiled-plugin")
    assert isinstance(mf, PluginManifest)
    assert mf.name == "my-compiled-plugin"
    assert mf.contributions.commands and len(mf.contributions.commands) == 5
