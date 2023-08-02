from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)

from . import PluginManager
from .manifest.utils import v1_to_v2
from .types import FullLayerData, LayerData

if TYPE_CHECKING:
    import napari.layers

    from .manifest.contributions import ReaderContribution, WriterContribution


def read(
    paths: List[str], *, stack: bool, plugin_name: Optional[str] = None
) -> List[LayerData]:
    """Try to read file at `path`, with plugins offering a ReaderContribution.

    Parameters
    ----------
    paths : list of str
        Path to the file or resource being read.
    stack : bool
        Should the readers stack the read files.
    plugin_name : str, optional
        Optional plugin name.  If provided, only readers from this plugin will be
        tried (it's possible that none will be compatible). by default None

    Returns
    -------
    List[LayerData]
        If a compatible reader is found and executed, a list of LayerDataTuples is
        returned

    Raises
    ------
    ValueError
        If no readers are found or none return data
    """
    assert isinstance(paths, list)
    return _read(paths, plugin_name=plugin_name, stack=stack)


def read_get_reader(
    path: Union[str, Sequence[str]],
    *,
    plugin_name: Optional[str] = None,
    stack: Optional[bool] = None,
) -> Tuple[List[LayerData], ReaderContribution]:
    """Variant of `read` that also returns the `ReaderContribution` used."""
    if stack is None:
        # "npe1" old path
        # Napari 0.4.15 and older, hopefully we can drop this and make stack mandatory
        new_path, new_stack = v1_to_v2(path)
        return _read(
            new_path, plugin_name=plugin_name, return_reader=True, stack=new_stack
        )
    else:
        assert isinstance(path, list)
        for p in path:
            assert isinstance(p, str)
        return _read(path, plugin_name=plugin_name, return_reader=True, stack=stack)


def write(
    path: str,
    layer_data: List[Union[FullLayerData, napari.layers.Layer]],
    *,
    plugin_name: Optional[str] = None,
) -> List[str]:
    """Write layer_data tuples to `path`.

    Parameters
    ----------
    path : str
        The path (file, directory, url) to write.
    layer_data : list of layer data tuples
        List of tuples in the form (data, metadata_dict, layer_type_string)
    plugin_name : str, optional
        Name of the plugin to write data with. If `None` then all plugins
        corresponding to appropriate hook specification will be looped
        through to find the first one that can write the data.

    Returns
    -------
    list of str
        List of file paths that were written

    Raises
    ------
    ValueError
        If no suitable writers are found.
    """
    return _write(path, layer_data, plugin_name=plugin_name)


def write_get_writer(
    path: str,
    layer_data: List[Union[FullLayerData, napari.layers.Layer]],
    *,
    plugin_name: Optional[str] = None,
) -> Tuple[List[str], WriterContribution]:
    """Variant of write that also returns the `WriterContribution` used."""
    return _write(path, layer_data, plugin_name=plugin_name, return_writer=True)


# -----------------------------------------------------------------------------------


@overload
def _read(
    paths: Union[str, Sequence[str]],
    *,
    stack: bool,
    plugin_name: Optional[str] = None,
    return_reader: Literal[False] = False,
    _pm=None,
) -> List[LayerData]:
    ...


@overload
def _read(
    paths: Union[str, Sequence[str]],
    *,
    stack: bool,
    plugin_name: Optional[str] = None,
    return_reader: Literal[True],
    _pm=None,
) -> Tuple[List[LayerData], ReaderContribution]:
    ...


def _read(
    paths: Union[str, Sequence[str]],
    *,
    stack: bool,
    plugin_name: Optional[str] = None,
    return_reader: bool = False,
    _pm: Optional[PluginManager] = None,
) -> Union[Tuple[List[LayerData], ReaderContribution], List[LayerData]]:
    """Execute the `read...` functions above."""
    if _pm is None:
        _pm = PluginManager.instance()

    # get readers compatible with paths and chosen plugin - raise errors if
    # choices are invalid or there's nothing to try
    chosen_compatible_readers = _get_compatible_readers_by_choice(
        plugin_name, paths, _pm
    )
    assert (
        chosen_compatible_readers
    ), "No readers to try. Expected an exception before this point."

    for rdr in chosen_compatible_readers:
        read_func = rdr.exec(
            kwargs={"path": paths, "stack": stack, "_registry": _pm.commands}
        )
        if read_func is not None:
            # if the reader function raises an exception here, we don't try to catch it
            if layer_data := read_func(paths, stack=stack):
                return (layer_data, rdr) if return_reader else layer_data

    if plugin_name:
        raise ValueError(
            f"Reader {plugin_name!r} was selected to open "
            + f"{paths!r}, but returned no data."
        )
    raise ValueError(f"No readers returned data for {paths!r}")


def _get_compatible_readers_by_choice(
    plugin_name: Union[str, None], paths: Union[str, Sequence[str]], pm: PluginManager
):
    """Returns compatible readers filtered by validated plugin choice.

    Checks that plugin_name is an existing plugin (and command if
    a specific contribution was passed), and that it is compatible
    with paths. Raises ValueError if given plugin doesn't exist,
    it is not compatible with the given paths, or no compatible
    readers can be found for paths (if no plugin was chosen).

    Parameters
    ----------
    plugin_name: Union[str, None]
        name of chosen plugin, or None
    paths: Union[str, Sequence[str]]
        paths to read
    pm: PluginManager
        plugin manager instance to check for readers

    Raises
    ------
    ValueError
        If the given reader doesn't exist
    ValueError
        If there are no compatible readers
    ValueError
        If the given reader is not compatible

    Returns
    -------
    compat_readers : List[ReaderContribution]
        Compatible readers for plugin choice
    """
    passed_contrib = plugin_name and ("." in plugin_name)
    compat_readers = list(pm.iter_compatible_readers(paths))
    compat_reader_names = sorted(
        {(rdr.command if passed_contrib else rdr.plugin_name) for rdr in compat_readers}
    )
    helper_error_message = (
        f"Available readers for {paths!r} are: {compat_reader_names!r}."
        if compat_reader_names
        else f"No compatible readers are available for {paths!r}."
    )

    # check whether plugin even exists.
    if plugin_name:
        try:
            # note that get_manifest works with a full command e.g. my-plugin.my-reader
            pm.get_manifest(plugin_name)
            if passed_contrib:
                pm.get_command(plugin_name)
        except KeyError:
            raise ValueError(
                f"Given reader {plugin_name!r} does not exist. {helper_error_message}"
            ) from None

    # no choice was made and there's no readers to try
    if not plugin_name and not len(compat_reader_names):
        raise ValueError(helper_error_message)

    # user didn't make a choice and we have some readers to try, return them
    if not plugin_name:
        return compat_readers

    # user made a choice and it exists, but it may not be a compatible reader
    plugin, _, _ = plugin_name.partition(".")
    chosen_compatible_readers = [
        rdr
        for rdr in compat_readers
        if rdr.plugin_name == plugin
        and (not passed_contrib or rdr.command == plugin_name)
    ]
    # the user's choice is not compatible with the paths. let them know what is
    if not chosen_compatible_readers:
        raise ValueError(
            f"Given reader {plugin_name!r} is not a compatible reader for {paths!r}. "
            + helper_error_message
        )
    return chosen_compatible_readers


@overload
def _write(
    path: str,
    layer_data: List[Union[FullLayerData, napari.layers.Layer]],
    *,
    plugin_name: Optional[str] = None,
    return_writer: Literal[False] = False,
    _pm: Optional[PluginManager] = None,
) -> List[str]:
    ...


@overload
def _write(
    path: str,
    layer_data: List[Union[FullLayerData, napari.layers.Layer]],
    *,
    plugin_name: Optional[str] = None,
    return_writer: Literal[True],
    _pm: Optional[PluginManager] = None,
) -> Tuple[List[str], WriterContribution]:
    ...


def _write(
    path: str,
    layer_data: List[Union[FullLayerData, napari.layers.Layer]],
    *,
    plugin_name: Optional[str] = None,
    return_writer: bool = False,
    _pm: Optional[PluginManager] = None,
) -> Union[List[str], Tuple[List[str], WriterContribution]]:
    if not layer_data:
        raise ValueError("Must provide layer data")
    if _pm is None:
        _pm = PluginManager.instance()

    _layer_tuples: List[FullLayerData] = [
        cast("napari.layers.Layer", x).as_layer_data_tuple()
        if hasattr(x, "as_layer_data_tuple")
        else x
        for x in layer_data
    ]
    layer_types = [x[2] for x in _layer_tuples]
    writer, new_path = _pm.get_writer(
        path, layer_types=layer_types, plugin_name=plugin_name
    )

    if not writer:
        raise ValueError(f"No writer found for {path!r} with layer types {layer_types}")

    # Writers that take at most one layer must use the single-layer api.
    # Otherwise, they must use the multi-layer api.
    n = sum(ltc.max() for ltc in writer.layer_type_constraints())
    args = (new_path, *_layer_tuples[0][:2]) if n <= 1 else (new_path, _layer_tuples)
    res = writer.exec(args=args)

    # napari_get_writer-style writers don't always return a list
    # though strictly speaking they should?
    result = [res] if isinstance(res, str) else res or []  # type: ignore
    return (result, writer) if return_writer else result
