from pathlib import Path

import pytest

from npe2._inspection import compile
from npe2.manifest.schema import PluginManifest


def test_compile(compiled_plugin_dir: Path, tmp_path: Path):
    """
    Test that the plugin manager can be compiled.
    """
    with pytest.raises(ValueError, match="must have an extension of .json, .yaml, or"):
        compile(compiled_plugin_dir, "bad_path")

    dest = tmp_path / "output.yaml"
    mf = compile(compiled_plugin_dir, dest=dest, packages=["my_module"])
    assert isinstance(mf, PluginManifest)
    assert mf.name == "my_compiled_plugin"
    assert mf.contributions.commands and len(mf.contributions.commands) == 5
    assert dest.exists()
    assert PluginManifest.from_file(dest) == mf


def test_compile_with_template(compiled_plugin_dir: Path, tmp_path: Path):
    """Test building from a template with npe2 compile."""
    template = tmp_path / "template.yaml"
    template.write_text("name: my_compiled_plugin\ndisplay_name: Display Name\n")
    mf = compile(compiled_plugin_dir, template=template)
    assert mf.name == "my_compiled_plugin"
    assert mf.display_name == "Display Name"
