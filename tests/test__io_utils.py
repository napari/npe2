# extra underscore in name to run this first

import pytest

from npe2 import (
    DynamicPlugin,
    PluginManager,
    io_utils,
    read,
    read_get_reader,
    write,
    write_get_writer,
)
from npe2.types import FullLayerData

SAMPLE_PLUGIN_NAME = "my-plugin"


def test_read(uses_sample_plugin):
    assert read(["some.fzzy"], stack=False) == [(None,)]


def test_read_with_unknown_plugin(uses_sample_plugin):
    # no such plugin name.... skips over the sample plugin & error is specific
    with pytest.raises(ValueError, match="Plugin 'nope' was selected"):
        read(["some.fzzy"], plugin_name="nope", stack=False)


def test_read_with_no_plugin():
    # no plugin passed and none registered
    with pytest.raises(ValueError, match="No readers returned"):
        read(["some.nope"], stack=False)


def test_read_return_reader(uses_sample_plugin):
    data, reader = read_get_reader("some.fzzy")
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


def test_read_non_global_pm():
    pm = PluginManager()
    plugin = DynamicPlugin("my-plugin", plugin_manager=pm)

    @plugin.contribute.reader
    def read_path(path):
        def _reader(path):
            return [(None,)]

        return _reader

    assert io_utils._read(["some.fzzy"], stack=False, _pm=pm) == [(None,)]


def test_read_uppercase_extension():
    pm = PluginManager()
    plugin = DynamicPlugin("tif-plugin", plugin_manager=pm)
    path = "something.TIF"

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.tif"])
    def get_read(path):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match="Given path contains capitals."):
        io_utils._read([path], stack=False, _pm=pm)


@pytest.mark.parametrize(
    "path", ["some_zarr_directory.ZARR", "some_zarr_directory.Zarr"]
)
def test_read_zarr_variants(path: str, tmp_path: Path):
    new_dir = tmp_path / path 
    new_dir.mkdir()
    pm = PluginManager()
    plugin = DynamicPlugin("zarr-plugin", plugin_manager=pm)

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.zarr"], accepts_directories=True)
    def get_read(path):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match="Given path contains capitals."):
        io_utils._read([path], stack=False, _pm=pm)


@pytest.mark.parametrize(
    "path", ["some_two_ext_file.TAR.gz", "some_two_ext_file.TAR.GZ"]
)
def test_read_tar_gz_variants(path: str):
    pm = PluginManager()
    plugin = DynamicPlugin("tar-gz-plugin", plugin_manager=pm)

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.tar.gz"])
    def get_read(path):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match="Given path contains capitals."):
        io_utils._read([path], stack=False, _pm=pm)


@pytest.mark.parametrize("path", ["some_directory.Final", "some_directory.FINAL"])
def test_read_directory_variants(path: str):
    pm = PluginManager()
    plugin = DynamicPlugin("directory-plugin", plugin_manager=pm)

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.final"], accepts_directories=True)
    def get_read(path):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match="Given path contains capitals."):
        io_utils._read([path], stack=False, _pm=pm)
