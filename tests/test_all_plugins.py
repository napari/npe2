import os

import pytest

PLUGIN = os.getenv("TEST_PACKAGE_NAME")
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore


def test_entry_points():
    assert PLUGIN
    d = metadata.distribution(str(PLUGIN))
    eps = [
        ep for ep in d.entry_points if ep.group in ("napari.plugin", "napari.manifest")
    ]
    assert eps
    print(eps)
