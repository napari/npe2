import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from npe2 import PluginManifest


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "sample"


@pytest.fixture
def uses_sample_plugin(sample_path):
    sys.path.append(str(sample_path))
    yield
    sys.path.remove(str(sample_path))


@pytest.fixture(autouse=True)
def mock_discover():
    _discover = PluginManifest.discover

    def wrapper(*args, **kwargs):
        before = sys.path.copy()
        # only allowing things from test directory in discover
        sys.path = [x for x in sys.path if str(Path(__file__).parent) in x]
        try:
            yield from _discover(*args, **kwargs)
        finally:
            sys.path = before

    with patch("npe2.PluginManifest.discover", wraps=wrapper):
        yield
