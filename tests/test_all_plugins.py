import os
from typing import TYPE_CHECKING

import pytest

from npe2.cli import app

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN: str = os.getenv("TEST_PACKAGE_NAME") or ""
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


def test_fetch(tmp_path: "Path"):
    from typer.testing import CliRunner

    mf_file = tmp_path / "manifest.yaml"

    result = CliRunner().invoke(app, ["fetch", PLUGIN, "-o", str(mf_file)])
    assert result.exit_code == 0
    assert PLUGIN in mf_file.read_text()
    result2 = CliRunner().invoke(app, ["validate", str(mf_file)])
    assert result2.exit_code == 0
