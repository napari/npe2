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
    stack: bool = None,
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

    for rdr in _pm.iter_compatible_readers(paths):
        if plugin_name and not rdr.command.startswith(plugin_name):
            continue
        read_func = rdr.exec(kwargs={"path": paths, "stack": stack})
        if read_func is not None:
            # if the reader function raises an exception here, we don't try to catch it
            if layer_data := read_func(paths, stack=stack):
                return (layer_data, rdr) if return_reader else layer_data
    raise ValueError(f"No readers returned data for {paths!r}")


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
