import sys
from pathlib import Path

import pytest


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "sample"


@pytest.fixture
def uses_sample_plugin(sample_path):
    sys.path.append(str(sample_path))
    yield
    sys.path.remove(str(sample_path))
