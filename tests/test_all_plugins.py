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

FORGOT_NAPARI = [
    "vessel-express",
    "RedLionfish",
    "smo",
    "napari-yolov5",
    "napari-timeseries-opener-plugin",  # really just qtpy, magicgui, and tifffile
    "napari-nucleaizer",
    "napari-mri",
    "napari-dexp",
    "empanada-napari",
    "napari-bigwarp",
]


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


if PLUGIN in FORGOT_NAPARI:
    m = pytest.mark.xfail(reason="plugin forgot to list napari in deps", strict=True)
else:
    m = lambda f: f  # noqa


@m
def test_entry_points_importable(entry_points: List[metadata.EntryPoint]):
    for ep in entry_points:
        if ep.group == "napari.plugin":
            ep.load()
