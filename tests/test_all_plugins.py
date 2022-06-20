import os
from importlib import metadata
from typing import TYPE_CHECKING

import pytest

from npe2 import PluginManifest
from npe2._fetch import isolated_plugin_env
from npe2.cli import app

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN: str = os.getenv("TEST_PACKAGE_NAME") or ""
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


@pytest.fixture(scope="session")
def plugin_env():
    with isolated_plugin_env(PLUGIN) as env:
        yield env


def test_entry_points_importable(plugin_env):
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

    result = CliRunner().invoke(app, ["fetch", PLUGIN])
    assert result.exit_code == 0
    (out := tmp_path / "out.yaml").write_text(result.output)
    assert PluginManifest.from_file(out)
