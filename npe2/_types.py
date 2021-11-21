from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Sequence, Tuple, Union

from typing_extensions import Literal, Protocol

if TYPE_CHECKING:
    import numpy as np
    from magicgui.widgets import FunctionGui
    from qtpy.QtWidgets import QWidget


class ArrayLike(Protocol):
    shape: Tuple[int, ...]
    ndim: int
    dtype: "np.dtype"

    def __array__(self) -> "np.ndarray":
        ...


LayerName = Union[
    Literal["image"],
    Literal["labels"],
    Literal["points"],
    Literal["shapes"],
    Literal["surface"],
    Literal["tracks"],
    Literal["vectors"],
]
Metadata = Dict
DataType = Union[ArrayLike, Sequence[ArrayLike]]
FullLayerData = Tuple[DataType, Metadata, LayerName]
LayerData = Union[Tuple[DataType], Tuple[DataType, Metadata], FullLayerData]
PathLike = Union[str, Path]
PathOrPaths = Union[PathLike, Sequence[PathLike]]
ReaderFunction = Callable[[PathOrPaths], List[LayerData]]
WriterFunction = Callable[[str, List[FullLayerData]], List[str]]
Widget = Union["FunctionGui", "QWidget"]
WidgetCallable = Callable[..., Widget]
