from typing import List, Optional, Tuple, Union, overload

from typing_extensions import Literal

from ._types import LayerData, PathLike
from .manifest.io import ReaderContribution


@overload
def read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: Literal[False] = False,
    _pm=None,
) -> Optional[List[LayerData]]:
    ...


@overload
def read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: Literal[True],
    _pm=None,
) -> Optional[Tuple[List[LayerData], ReaderContribution]]:
    ...


def read(
    path: PathLike,
    *,
    plugin_name: Optional[str] = None,
    return_reader: bool = False,
    _pm=None,
) -> Optional[Union[Tuple[List[LayerData], ReaderContribution], List[LayerData]]]:
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
    List[LayerData], optional
        If a compatible reader is found and executed, a list of LayerDataTuples is
        returned. Otherwise None is returned.
    """
    if _pm is None:
        from . import PluginManager

        pm = PluginManager.instance()

    for rdr in pm.iter_compatible_readers(path):
        if plugin_name and not rdr.command.startswith(plugin_name):
            continue
        read_func = rdr.exec(kwargs={"path": path})
        if read_func is not None:
            try:
                layer_data = read_func(path)
                if layer_data:
                    return (layer_data, rdr) if return_reader else layer_data
            except Exception:
                # TODO: what here.
                # a plugin has successfully passed the extension check, and returned
                # a reader callable, but that callable has failed. How do we make this
                # easy for developer to debug, but not too annoying for a user.
                # should we be returning a list of exceptions?
                continue
    return None
