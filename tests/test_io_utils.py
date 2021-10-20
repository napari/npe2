from npe2.io_utils import read


def test_read(uses_sample_plugin):
    assert read("some.fzzy") == [(None,)]


def test_read_with_plugin(uses_sample_plugin):
    # no such plugin name.... but skips over the sample plugin
    assert read("some.fzzy", plugin_name="nope") is None


def test_read_return_reader(uses_sample_plugin):
    result = read("some.fzzy", return_reader=True)
    assert result
    data, reader = result
    assert data == [(None,)]
    assert reader.command == "my_plugin.some_reader"
