# extra underscore in name to run this first

import pytest

from npe2 import read, read_get_reader, write, write_get_writer
from npe2.types import FullLayerData

SAMPLE_PLUGIN_NAME = "my-plugin"


def test_read(uses_sample_plugin):
    assert read(["some.fzzy"], stack=False) == [(None,)]


def test_read_with_unknown_plugin(uses_sample_plugin):
    # no such plugin name.... skips over the sample plugin & error is specific
    with pytest.raises(ValueError, match="Plugin 'nope' was selected"):
        read(["some.fzzy"], plugin_name="nope", stack=False)


def test_read_uppercase_extension(uses_sample_plugin):
    # sample plugin hard-codes lower case and returns this error
    # so the error ensures the matching was case-insensitive
    # and that the sample plugin received full path (with case)
    with pytest.raises(ValueError, match="Test plugin should"):
        read(["some.FZZY"], stack=False)


def test_read_with_no_plugin():
    # no plugin passed and none registered
    with pytest.raises(ValueError, match="No readers returned"):
        read(["some.nope"], stack=False)


def test_read_return_reader(uses_sample_plugin):
    data, reader = read_get_reader("some.fzzy")
    assert data == [(None,)]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_read_uppercase_extension_return_reader(uses_sample_plugin):
    # sample plugin hard-codes lower case and returns this error
    # so the error ensures the matching was case-insensitive
    # and that the sample plugin received full path (with case)
    with pytest.raises(ValueError, match="Test plugin should"):
        data, reader = read_get_reader("some.FZZY")
        assert data == [(None,)]
        assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_read_return_reader_with_stack(uses_sample_plugin):
    data, reader = read_get_reader(["some.fzzy"], stack=True)
    assert data == [(None,)]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_read_list(uses_sample_plugin):
    data, reader = read_get_reader(["some.fzzy", "other.fzzy"])
    assert data == [(None,)]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


null_image: FullLayerData = ([], {}, "image")


def test_writer_exec(uses_sample_plugin):
    # the sample writer knows how to handle two image layers
    result = write("test.tif", [null_image, null_image])
    assert result == ["test.tif"]

    result, contrib = write_get_writer("test.tif", [null_image, null_image])
    assert result == ["test.tif"]
    assert contrib.command == f"{SAMPLE_PLUGIN_NAME}.my_writer"


@pytest.mark.parametrize("layer_data", [[null_image, null_image], []])
def test_writer_exec_fails(layer_data, uses_sample_plugin):
    # the sample writer doesn't accept no extension
    with pytest.raises(ValueError):
        write("test/path", layer_data)


def test_writer_exec_fails2(uses_sample_plugin):
    # the sample writer doesn't accept 5 images
    with pytest.raises(ValueError):
        write("test.tif", [null_image, null_image, null_image, null_image, null_image])


def test_writer_single_layer_api_exec(uses_sample_plugin):
    # This writer doesn't do anything but type check.
    paths = write("test/path", [([], {}, "labels")])
    assert len(paths) == 1
