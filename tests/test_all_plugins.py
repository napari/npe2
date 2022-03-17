import os
from typing import List

import pytest

PLUGIN = os.getenv("TEST_PACKAGE_NAME")
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


@pytest.fixture
def entry_points():
    d = metadata.distribution(str(PLUGIN))
    return [
        ep for ep in d.entry_points if ep.group in ("napari.plugin", "napari.manifest")
    ]


def test_plugin_has_entry_points(entry_points):
    if PLUGIN not in {"napari-console", "napari-error-reporter"}:
        assert entry_points
        print("EPs:", entry_points)


def test_entry_points_importable(entry_points: List[metadata.EntryPoint]):
    for ep in entry_points:
        if ep.group == "napari.plugin":
            ep.load()
