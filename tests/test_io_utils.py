import pytest

from npe2.io_utils import read, read_get_reader


def test_read(uses_sample_plugin):
    assert read("some.fzzy") == [(None,)]


def test_read_with_plugin(uses_sample_plugin):
    # no such plugin name.... but skips over the sample plugin
    with pytest.raises(ValueError):
        read("some.fzzy", plugin_name="nope")


def test_read_return_reader(uses_sample_plugin):
    data, reader = read_get_reader("some.fzzy")
    assert data == [(None,)]
    assert reader.command == "my_plugin.some_reader"
