# Types for GUI HookSpecs
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Sequence,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from typing import TypedDict

    from magicgui.widgets import FunctionGui
    from qtpy.QtWidgets import QWidget

WidgetCallable = Callable[..., Union["FunctionGui", "QWidget"]]
AugmentedWidget = Union[WidgetCallable, Tuple[WidgetCallable, dict]]

# layer data may be: (data,) (data, meta), or (data, meta, layer_type)
# using "Any" for the data type until ArrayLike is more mature.
FullLayerData = Tuple[Any, Dict, str]
LayerData = Union[Tuple[Any], Tuple[Any, Dict], FullLayerData]
PathLike = Union[str, Path]
PathOrPaths = Union[PathLike, Sequence[PathLike]]

ReaderFunction = Callable[[PathOrPaths], List[LayerData]]
WriterFunction = Callable[[str, List[FullLayerData]], List[str]]

# Sample Data for napari_provide_sample_data hookspec is either a string/path
# or a function that returns an iterable of LayerData tuples
SampleData = Union[PathLike, Callable[..., Iterable[LayerData]]]


# or... they can provide a dict as follows:
class SampleDict(TypedDict):
    display_name: str
    data: SampleData
