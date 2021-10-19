from typing import List, Optional

from ._types import LayerData, PathLike


def read(path: PathLike, plugin=None) -> Optional[List[LayerData]]:
    """Try to return data for `path`, from reader plugins using a manifest."""
    from . import PluginManager

    if plugin is not None:
        ...  # handle specific plugin

    for rdr in PluginManager.instance().iter_compatible_readers(path):
        read_func = rdr.exec(kwargs={"path": path})
        if read_func is not None:
            try:
                layer_data = read_func(path)  # try to read data
                if layer_data:
                    return layer_data
            except Exception:
                # TODO: what here.  @carreau?
                continue
    return None
