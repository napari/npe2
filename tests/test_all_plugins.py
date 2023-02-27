import os
from importlib import metadata
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest

from npe2._inspection._full_install import isolated_plugin_env
from npe2.cli import app

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN: str = os.getenv("TEST_PACKAGE_NAME") or ""
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


@pytest.fixture(scope="session")
def plugin_env():
    try:
        with isolated_plugin_env(PLUGIN) as env:
            yield env
    except CalledProcessError as e:
        if "Failed building wheel" in str(e.output):
            yield None


def test_entry_points_importable(plugin_env):
    if plugin_env is None:
        pytest.mark.xfail()
        return

    entry_points = [
        ep
        for ep in metadata.distribution(PLUGIN).entry_points
        if ep.group in ("napari.plugin", "napari.manifest")
    ]
    if PLUGIN not in {"napari-console", "napari-error-reporter"}:
        assert entry_points

    for ep in entry_points:
        if ep.group == "napari.plugin":
            ep.load()


def test_fetch(tmp_path: "Path"):
    from typer.testing import CliRunner

    mf_file = tmp_path / "manifest.yaml"

    result = CliRunner().invoke(app, ["fetch", PLUGIN, "-o", str(mf_file)])
    assert result.exit_code == 0
    assert PLUGIN in mf_file.read_text()
    result2 = CliRunner().invoke(app, ["validate", str(mf_file)])
    assert result2.exit_code == 0
