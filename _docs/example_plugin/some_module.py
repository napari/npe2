# python_name: example_plugin._data:fractal

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from magicgui import magic_factory
from qtpy.QtWidgets import QWidget

if TYPE_CHECKING:
    import napari.types
    import napari.viewer
    from npe2.types import LayerData, PathOrPaths, ReaderFunction


def write_points(path: str, layer_data: Any, attributes: Dict[str, Any]) -> List[str]:
    with open(path, "w"):
        ...  # save layer_data and attributes to file

    # return path to any file(s) that were successfully written
    return [path]


def get_reader(path: "PathOrPaths") -> Optional["ReaderFunction"]:
    # If we recognize the format, we return the actual reader function
    if isinstance(path, str) and path.endswith(".xyz"):
        return xyz_file_reader
    # otherwise we return None.
    return None


def xyz_file_reader(path: "PathOrPaths") -> List["LayerData"]:
    data = ...  # somehow read data from path
    layer_attributes = {"name": "etc..."}
    return [(data, layer_attributes)]


class MyWidget(QWidget):
    """Any QtWidgets.QWidget or magicgui.widgets.Widget subclass can be used."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        ...


@magic_factory
def widget_factory(
    image: "napari.types.ImageData", threshold: int
) -> "napari.types.LabelsData":
    """Generate thresholded image.

    This pattern uses magicgui.magic_factory directly to turn a function
    into a callable that returns a widget.
    """
    return (image > threshold).astype(int)


def threshold(
    image: "napari.types.ImageData", threshold: int
) -> "napari.types.LabelsData":
    """Generate thresholded image.

    This function will be turned into a widget using `autogenerate: true`.
    """
    return (image > threshold).astype(int)


def create_fractal() -> List["LayerData"]:
    """An example of a  Sample Data Function.

    Note: Sample Data with URIs don't need python code.
    """
    data = ...  # do something cool to create a fractal
    return [(data, {"name": "My cool fractal"})]
