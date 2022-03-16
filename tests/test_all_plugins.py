import os
from importlib import metadata

import pytest

PLUGIN = os.getenv("TEST_PACKAGE_NAME")
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


def test_entry_points():
    dist = metadata.distribution(str(PLUGIN))
    print(dist.entry_points)
