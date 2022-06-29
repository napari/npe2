from npe2.implements import compile
import pytest
from pathlib import Path
import shutil

FIXTURES = Path(__file__).parent / 'fixtures'

@pytest.fixture
def compiled_plugin_dir(tmp_path):
    shutil.copytree(FIXTURES / 'my-compiled-plugin', tmp_path, dirs_exist_ok=True)
    return tmp_path

def test_compile(compiled_plugin_dir):
    """
    Test that the plugin manager can be compiled.
    """
    mf = compile(compiled_plugin_dir)
