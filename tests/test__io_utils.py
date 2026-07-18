# extra underscore in name to run this first
import logging
from pathlib import Path
from unittest.mock import patch

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
    paths = ["some.fzzy"]
    chosen_reader = "not-a-plugin"
    with pytest.raises(
        ValueError, match=f"Given reader {chosen_reader!r} does not exist."
    ) as e:
        read(paths, plugin_name=chosen_reader, stack=False)
    assert f"Available readers for {paths!r} are: {[SAMPLE_PLUGIN_NAME]!r}" in str(e)


def test_read_with_unknown_plugin_no_readers(uses_sample_plugin):
    paths = ["some.nope"]
    chosen_reader = "not-a-plugin"
    with pytest.raises(
        ValueError, match=f"Given reader {chosen_reader!r} does not exist."
    ) as e:
        read(paths, plugin_name=chosen_reader, stack=False)
    assert "No compatible readers are available" in str(e)


def test_read_with_no_plugin():
    # no plugin passed and none registered
    paths = ["some.nope"]
    with pytest.raises(ValueError, match="No compatible readers are available"):
        read(paths, stack=False)


def test_read_uses_correct_passed_plugin(tmp_path, caplog):
    pm = PluginManager()
    long_name = "gooby-again"
    short_name = "gooby"
    long_name_plugin = DynamicPlugin(long_name, plugin_manager=pm)
    short_name_plugin = DynamicPlugin(short_name, plugin_manager=pm)

    long_name_plugin.register()
    short_name_plugin.register()

    path = "something.fzzy"
    mock_file = tmp_path / path
    mock_file.touch()

    @long_name_plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read_long(path=mock_file):
        raise ValueError(
            f"Uhoh, {long_name} was chosen, but given plugin was {short_name}"
        )

    @short_name_plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read(path=mock_file):
        def read(paths):
            return [(None,)]

        return read

    # "gooby-again" isn't used even though given plugin starts with the same name
    # the reader from "gooby" returns [(None,)] which is successfully returned
    caplog.set_level(logging.DEBUG, logger="npe2.io_utils")
    result = io_utils._read(["some.fzzy"], plugin_name=short_name, stack=False, _pm=pm)
    assert result == [(None,)]
    assert any(
        rf"Reader {short_name!r} was selected" in rec.message for rec in caplog.records
    )


def test_pathlib_normalized_to_str_for_plugins():
    """Plugins must keep receiving ``str`` even when callers pass ``Path``.

    Existing reader plugins assume ``str`` (e.g. ``path.startswith(...)``), so
    npe2 normalises ``pathlib.Path`` to ``str`` before dispatching.
    """
    pm = PluginManager()
    plugin = DynamicPlugin("str-only", plugin_manager=pm)
    plugin.register()

    received: dict = {}

    @plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read(path):
        received["getter"] = path

        def reader_func(paths):
            received["reader"] = paths
            return [(None,)]

        return reader_func

    io_utils._read([Path("some.fzzy")], stack=False, _pm=pm)
    assert isinstance(received["getter"], str)
    # the reader function receives the (normalised) list of str paths
    assert all(isinstance(p, str) for p in received["reader"])


def test_read_fails_with_refused_reader():
    pm = PluginManager()
    plugin_name = "always-fails"
    plugin = DynamicPlugin(plugin_name, plugin_manager=pm)
    plugin.register()

    @plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read(path):
        return None

    with pytest.raises(
        ValueError, match=f"Reader {plugin_name!r} was selected .* refused the file"
    ):
        io_utils._read(["some.fzzy"], plugin_name=plugin_name, stack=False, _pm=pm)

    with pytest.raises(ValueError, match="No readers returned data"):
        io_utils._read(["some.fzzy"], stack=False, _pm=pm)


def test_read_succeeds_with_null_layer_and_chosen_plugin(caplog):
    """A selected reader returning [(None,)] is valid — it signals
    'file processed successfully, nothing to add to the viewer'.
    A DEBUG log message is issued when a plugin was explicitly chosen."""
    pm = PluginManager()
    plugin_name = "always-fails"
    plugin = DynamicPlugin(plugin_name, plugin_manager=pm)
    plugin.register()

    def reader_func(path):
        return [(None,)]

    @plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read(path):
        return reader_func

    caplog.set_level(logging.DEBUG, logger="npe2.io_utils")
    result = io_utils._read(["some.fzzy"], plugin_name=plugin_name, stack=False, _pm=pm)
    assert result == [(None,)]
    assert any(
        rf"Reader {plugin_name!r} was selected" in rec.message for rec in caplog.records
    )


def test_read_fails_with_reader_returning_none():
    pm = PluginManager()
    plugin_name = "none-reader"
    plugin = DynamicPlugin(plugin_name, plugin_manager=pm)
    plugin.register()

    def reader_func(path):
        return None

    @plugin.contribute.reader(filename_patterns=["*.fzzy"])
    def get_read(path):
        return reader_func

    with pytest.raises(
        ValueError, match=f"Reader {plugin_name!r} was selected .* returned no data"
    ):
        io_utils._read(["some.fzzy"], plugin_name=plugin_name, stack=False, _pm=pm)

    with pytest.raises(ValueError, match="No readers returned data"):
        io_utils._read(["some.fzzy"], stack=False, _pm=pm)


def test_read_with_incompatible_reader(uses_sample_plugin):
    paths = ["some.notfzzy"]
    chosen_reader = f"{SAMPLE_PLUGIN_NAME}"
    with pytest.raises(
        ValueError, match=f"Given reader {chosen_reader!r} is not a compatible reader"
    ):
        read(paths, stack=False, plugin_name=chosen_reader)


def test_read_with_no_compatible_reader():
    paths = ["some.notfzzy"]
    with pytest.raises(ValueError, match="No compatible readers are available"):
        read(paths, stack=False)


def test_read_with_reader_contribution_plugin(uses_sample_plugin, caplog):
    paths = ["some.fzzy"]
    chosen_reader = f"{SAMPLE_PLUGIN_NAME}.some_reader"
    caplog.set_level(logging.DEBUG, logger="npe2.io_utils")
    result = read(paths, stack=False, plugin_name=chosen_reader)
    assert result == [(None,)]
    assert any(
        rf"Reader {chosen_reader!r} was selected" in rec.message
        for rec in caplog.records
    )

    # if the wrong contribution is passed we get useful error message
    chosen_reader = f"{SAMPLE_PLUGIN_NAME}.not_a_reader"
    with pytest.raises(
        ValueError,
        match=f"Given reader {chosen_reader!r} does not exist.",
    ) as e:
        read(paths, stack=False, plugin_name=chosen_reader)
    assert "Available readers for" in str(e)


def test_read_assertion_with_no_compatible_readers(uses_sample_plugin):
    paths = ["some.noreader"]
    with patch("npe2.io_utils._get_compatible_readers_by_choice", return_value=[]):
        with pytest.raises(AssertionError, match=r"No readers to try."):
            read(paths, stack=False)


def test_available_readers_show_commands(uses_sample_plugin):
    paths = ["some.fzzy"]
    chosen_reader = "not-a-plugin.not-a-reader"
    with pytest.raises(
        ValueError,
        match=f"Given reader {chosen_reader!r} does not exist.",
    ) as e:
        read(paths, stack=False, plugin_name=chosen_reader)
    assert "Available readers " in str(e)
    assert f"{SAMPLE_PLUGIN_NAME}.some_reader" in str(e)

    chosen_reader = "not-a-plugin"
    with pytest.raises(
        ValueError,
        match=f"Given reader {chosen_reader!r} does not exist.",
    ) as e:
        read(paths, stack=False, plugin_name=chosen_reader)
    assert "Available readers " in str(e)
    assert f"{SAMPLE_PLUGIN_NAME}.some_reader" not in str(e)
    assert f"{SAMPLE_PLUGIN_NAME}" in str(e)


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


def test_read_pathlib(uses_sample_plugin):
    """pathlib.Path inputs are accepted, not only str."""
    assert read([Path("some.fzzy")], stack=False) == [(None,)]


def test_read_return_reader_pathlib(uses_sample_plugin):
    """pathlib.Path inputs are accepted by read_get_reader (npe1 path)."""
    data, reader = read_get_reader(Path("some.fzzy"))
    assert data == [(None,)]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


def test_read_list_pathlib(uses_sample_plugin):
    """A stacked list of pathlib.Path inputs is accepted."""
    data, reader = read_get_reader([Path("some.fzzy"), Path("other.fzzy")])
    assert data == [(None,)]
    assert reader.command == f"{SAMPLE_PLUGIN_NAME}.some_reader"


null_image: FullLayerData = ([], {}, "image")


def test_get_writer_compound_extension():
    """Writer selection prefers the longest matching extension, so ``.ome.tiff``
    and ``.ome.zarr`` win over higher-priority plain ``.tiff`` / ``.zarr``
    writers. Regression test for napari/napari#9088.
    """
    pm = PluginManager()
    with DynamicPlugin(name="fmt-plugin", plugin_manager=pm) as plg:
        # Registered first, so the plain writers also have higher priority.
        @plg.contribute.writer(
            filename_extensions=["*.tif", "*.tiff"], layer_types=["image"]
        )
        def tiff_writer(path, data): ...

        @plg.contribute.writer(filename_extensions=["*.zarr"], layer_types=["image"])
        def zarr_writer(path, data): ...

        @plg.contribute.writer(
            filename_extensions=["*.ome.tif", "*.ome.tiff"], layer_types=["image"]
        )
        def ome_tiff_writer(path, data): ...

        @plg.contribute.writer(
            filename_extensions=["*.ome.zarr"], layer_types=["image"]
        )
        def ome_zarr_writer(path, data): ...

        # (path, expected writer command, expected returned path)
        cases = [
            ("img.ome.tiff", "fmt-plugin.ome_tiff_writer", "img.ome.tiff"),
            ("img.ome.tif", "fmt-plugin.ome_tiff_writer", "img.ome.tif"),
            ("img.tiff", "fmt-plugin.tiff_writer", "img.tiff"),
            ("img.tif", "fmt-plugin.tiff_writer", "img.tif"),
            ("img.ome.zarr", "fmt-plugin.ome_zarr_writer", "img.ome.zarr"),
            ("img.zarr", "fmt-plugin.zarr_writer", "img.zarr"),
            # No extension: first writer wins, its default extension appended.
            ("img", "fmt-plugin.tiff_writer", "img.tif"),
        ]
        for path, expected_cmd, expected_out in cases:
            writer, out = pm.get_writer(path, ["image"])
            assert writer is not None, f"no writer selected for {path!r}"
            assert writer.command == expected_cmd, path
            assert out == expected_out, path


def test_writer_exec(uses_sample_plugin):
    # the sample writer knows how to handle two image layers
    result = write("test.tif", [null_image, null_image])
    assert result == ["test.tif"]

    result, contrib = write_get_writer("test.tif", [null_image, null_image])
    assert result == ["test.tif"]
    assert contrib.command == f"{SAMPLE_PLUGIN_NAME}.my_writer"


def test_writer_exec_pathlib(uses_sample_plugin):
    """pathlib.Path inputs are accepted by the write helpers, returning str."""
    result = write(Path("test.tif"), [null_image, null_image])
    assert result == ["test.tif"]
    assert all(isinstance(p, str) for p in result)

    result, contrib = write_get_writer(Path("test.tif"), [null_image, null_image])
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


def test_read_uppercase_extension(tmp_path: Path):
    pm = PluginManager()
    plugin = DynamicPlugin("tif-plugin", plugin_manager=pm)

    path = "something.TIF"
    mock_file = tmp_path / path
    mock_file.touch()

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.tif"])
    def get_read(path=mock_file):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match=r"Given path contains capitals."):
        io_utils._read([str(mock_file)], stack=False, _pm=pm)


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

    with pytest.raises(ValueError, match=r"Given path contains capitals."):
        io_utils._read([str(new_dir)], stack=False, _pm=pm)


@pytest.mark.parametrize(
    "path", ["some_two_ext_file.TAR.gz", "some_two_ext_file.TAR.GZ"]
)
def test_read_tar_gz_variants(path: str, tmp_path: Path):
    pm = PluginManager()
    plugin = DynamicPlugin("tar-gz-plugin", plugin_manager=pm)

    mock_file = tmp_path / path
    mock_file.touch()

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*.tar.gz"])
    def get_read(path=mock_file):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match=r"Given path contains capitals."):
        io_utils._read([str(mock_file)], stack=False, _pm=pm)


@pytest.mark.parametrize("path", ["some_directory.Final", "some_directory.FINAL"])
def test_read_directory_variants(path: str, tmp_path: Path):
    new_dir = tmp_path / path
    new_dir.mkdir()
    pm = PluginManager()
    plugin = DynamicPlugin("directory-plugin", plugin_manager=pm)

    # reader should be compatible despite lowercase pattern
    @plugin.contribute.reader(filename_patterns=["*"], accepts_directories=True)
    def get_read(path):
        if path.lower() != path:
            # if this error is raised we can be certain path is unchanged
            raise ValueError("Given path contains capitals.")

        def read(paths):
            return [(None,)]

        return read

    with pytest.raises(ValueError, match=r"Given path contains capitals."):
        io_utils._read([str(new_dir)], stack=False, _pm=pm)
