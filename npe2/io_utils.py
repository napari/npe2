from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple, Union, overload

from typing_extensions import Literal

from . import PluginManager
from .types import FullLayerData, LayerData, PathLike

if TYPE_CHECKING:
    from .manifest.readers import ReaderContribution
    from .manifest.writers import WriterContribution


def read(path: PathLike, *, plugin_name: Optional[str] = None) -> List[LayerData]:
    """Try to read file at `path`, with plugins offering a ReaderContribution.

    Parameters
    ----------
    path : str or Path
        Path to the file or resource being read.
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
    return _read(path, plugin_name=plugin_name)


def read_get_reader(
    path: PathLike, *, plugin_name: Optional[str] = None
) -> Tuple[List[LayerData], ReaderContribution]:
    """Variant of `read` that also returns the `ReaderContribution` used."""
    return _read(path, plugin_name=plugin_name, return_reader=True)


def write(
    path: str,
    layer_data: List[FullLayerData],
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
    layer_data: List[FullLayerData],
    *,
    plugin_name: Optional[str] = None,
) -> Tuple[List[str], WriterContribution]:
    """Variant of write that also returns the `WriterContribution` used."""
    return _write(path, layer_data, plugin_name=plugin_name, return_writer=True)


# -----------------------------------------------------------------------------------


@overload
def _read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: Literal[False] = False,
    _pm=None,
) -> List[LayerData]:
    ...


@overload
def _read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: Literal[True],
    _pm=None,
) -> Tuple[List[LayerData], ReaderContribution]:
    ...


def _read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: bool = False,
    _pm: Optional[PluginManager] = None,
) -> Union[Tuple[List[LayerData], ReaderContribution], List[LayerData]]:
    """Execute the `read...` functions above."""
    if _pm is None:
        _pm = PluginManager.instance()

    for rdr in _pm.iter_compatible_readers(path):
        if plugin_name and not rdr.command.startswith(plugin_name):
            continue
        read_func = rdr.exec(kwargs={"path": path})
        if read_func is not None:
            # if the reader function raises an exception here, we don't try to catch it
            layer_data = read_func(path)
            if layer_data:
                return (layer_data, rdr) if return_reader else layer_data
    raise ValueError(f"No readers returned data for {path!r}")


@overload
def _write(
    path: str,
    layer_data: List[FullLayerData],
    *,
    plugin_name: Optional[str] = None,
    return_writer: Literal[False] = False,
    _pm: Optional[PluginManager] = None,
) -> List[str]:
    ...


@overload
def _write(
    path: str,
    layer_data: List[FullLayerData],
    *,
    plugin_name: Optional[str] = None,
    return_writer: Literal[True],
    _pm: Optional[PluginManager] = None,
) -> Tuple[List[str], WriterContribution]:
    ...


def _write(
    path: str,
    layer_data: List[FullLayerData],
    *,
    plugin_name: Optional[str] = None,
    return_writer: bool = False,
    _pm: Optional[PluginManager] = None,
) -> Union[List[str], Tuple[List[str], WriterContribution]]:

    if not layer_data:
        raise ValueError("Must provide layer data")
    if _pm is None:
        _pm = PluginManager.instance()

    layer_types = [x[2] for x in layer_data]
    writer, new_path = _pm.get_writer(
        path, layer_types=layer_types, plugin_name=plugin_name
    )

    if not writer:
        raise ValueError(f"No writer found for {path!r} with layer types {layer_types}")

    # Writers that take at most one layer must use the single-layer api.
    # Otherwise, they must use the multi-layer api.
    n = sum(ltc.max() for ltc in writer.layer_type_constraints())
    args = (new_path, *layer_data[0][:2]) if n <= 1 else (new_path, layer_data)
    res = writer.exec(args=args)

    # napari_get_writer-style writers don't always return a list
    # though strictly speaking they should?
    result = [res] if isinstance(res, str) else res or []  # type: ignore
    return (result, writer) if return_writer else result
