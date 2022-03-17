import os
import warnings
from typing import List

import pytest

from npe2._from_npe1 import _python_name, iter_hookimpls
from npe2.manifest.utils import SHIM_NAME_PREFIX, import_python_name

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


PLUGIN = os.getenv("TEST_PACKAGE_NAME")
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


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
    depsfail = pytest.mark.xfail(reason="forgot napari in deps", strict=True)
elif PLUGIN == "napari-omero":
    depsfail = pytest.mark.xfail(reason="needs conda work", strict=True)
else:
    depsfail = lambda f: f  # noqa


@depsfail
def test_entry_points_importable(entry_points: List[metadata.EntryPoint]):
    for ep in entry_points:
        if ep.group == "napari.plugin":
            ep.load()


@depsfail
def test_npe1_python_names(entry_points: List[metadata.EntryPoint]):
    for ep in entry_points:
        if ep.group == "napari.plugin":
            for impl in iter_hookimpls(ep.load()):
                if impl.specname not in (
                    "napari_provide_sample_data",
                    "napari_experimental_provide_function",
                    "napari_experimental_provide_dock_widget",
                ):
                    continue

                result = impl.function()
                if isinstance(result, dict):
                    result = result.values()
                elif not isinstance(result, list):
                    result = [result]
                for idx, item in enumerate(result):
                    pyname = _python_name(item, impl.function, idx)
                    if SHIM_NAME_PREFIX in pyname:
                        warnings.warn("SHIMMING: %r" % pyname)
                    assert import_python_name(pyname) is not None
