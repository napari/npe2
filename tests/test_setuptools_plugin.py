import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from npe2 import PluginManifest

ROOT = Path(__file__).parent.parent

TEMPLATE = Path("my_module") / "_napari.yaml"
PYPROJECT = f"""
[build-system]
requires = ["setuptools", "wheel", "npe2 @ file://{ROOT}"]
build-backend = "setuptools.build_meta"

[tool.npe2]
template="{TEMPLATE}"
""".replace(
    "\\", "\\\\"
)


@pytest.mark.skipif(not os.getenv("CI"), reason="slow, only run on CI")
@pytest.mark.parametrize("dist_type", ["sdist", "wheel"])
def test_compile(compiled_plugin_dir: Path, tmp_path: Path, dist_type: str) -> None:
    """
    Test that the plugin manager can be compiled.
    """
    pyproject = compiled_plugin_dir / "pyproject.toml"
    pyproject.write_text(PYPROJECT)

    template = compiled_plugin_dir / TEMPLATE
    template.write_text("name: my_compiled_plugin\ndisplay_name: My Compiled Plugin\n")
    os.chdir(compiled_plugin_dir)
    subprocess.check_call([sys.executable, "-m", "build", f"--{dist_type}"])
    dist_dir = compiled_plugin_dir / "dist"
    assert dist_dir.is_dir()
    if dist_type == "sdist":
        # for sdist, test pip install into a temporary directory
        # and make sure the compiled manifest is there
        dist = next(dist_dir.glob("*.tar.gz"))
        site = tmp_path / "site"
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", str(dist), "--target", str(site)]
        )
        mf_file = site / "my_module" / "napari.yaml"
    else:
        # for wheel, make sure that the manifest is included in the wheel
        dist = next(dist_dir.glob("*.whl"))
        with zipfile.ZipFile(dist) as zip:
            zip.extractall(dist_dir)
        mf_file = dist_dir / "my_module" / "napari.yaml"

    assert mf_file.exists()
    mf = PluginManifest.from_file(mf_file)
    assert mf.display_name == "My Compiled Plugin"
    assert len(mf.contributions.readers) == 1
    assert len(mf.contributions.writers) == 2
