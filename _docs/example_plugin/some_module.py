# python_name: example_plugin._data:fractal

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from qtpy.QtWidgets import QWidget

from npe2.types import LayerData, PathOrPaths, ReaderFunction

if TYPE_CHECKING:
    import napari.types
    import napari.viewer


def write_points(path: str, layer_data: Any, properties: Dict[str, Any]) -> List[str]:
    with open(path, "w") as fh:
        ...  # save layer_data and properties to file

    # return path to any file(s) that were successfully written
    return [path]


def get_reader(path: PathOrPaths) -> Optional[ReaderFunction]:
    # If we recognize the format, we return the actual reader function
    if isinstance(path, str) and path.endswith("*.xyz"):
        return xyz_file_reader
    # otherwise we return None.
    return None


def xyz_file_reader(path: PathOrPaths) -> List[LayerData]:
    data = ...  # somehow read data from path
    layer_properties = {"name": "etc..."}
    return [(data, layer_properties)]


class AnimationWizard(QWidget):
    """Any QWidget or magicgui widget subclass can be used."""

    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        ...


def threshold(
    image: "napari.types.ImageData", threshold: int
) -> "napari.types.LabelsData":
    """Generate thresholded image.

    This function will be turned into a widget using `autogenerate: true`.
    """
    return (image > threshold).astype(int)


def create_fractal() -> List[LayerData]:
    data = ...  # do something cool to create a fractal
    return [(data, {"name": "My cool fractal"})]
