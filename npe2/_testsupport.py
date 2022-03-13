import pytest

from npe2 import TemporaryPlugin


@pytest.fixture
def temp_npe2_plugin():
    with TemporaryPlugin("fixture-plugin") as fp:
        yield fp


def test_contrib(temp_npe2_plugin: TemporaryPlugin):

    print("B")

    @temp_npe2_plugin.contribute.reader
    def make_image():
        return None

    pm = temp_npe2_plugin.plugin_manager
    print("C")
    assert list(pm.iter_sample_data())
