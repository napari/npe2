from typing import List, Optional

from ._types import LayerData, PathLike


def read(path: PathLike, plugin_name: str = None) -> Optional[List[LayerData]]:
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
    Optional[List[LayerData]]
        If a compatible reader is found and executed, a list of LayerDataTuples is
        returned.
    """
    from . import PluginManager

    for rdr in PluginManager.instance().iter_compatible_readers(path):
        if plugin_name and not rdr.command.startswith(plugin_name):
            continue
        read_func = rdr.exec(kwargs={"path": path})
        if read_func is not None:
            try:
                layer_data = read_func(path)
                if layer_data:
                    return layer_data
            except Exception:
                # TODO: what here.  @carreau?
                # a plugin has successfully passed the extension check, and returned
                # a reader callable, but that callable has failed. How do we make this
                # easy for developer to debug, but not too annoying for a user.
                continue
    return None
