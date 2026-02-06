from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Literal,
    NewType,
    Protocol,
    Union,
)

if TYPE_CHECKING:
    import magicgui.widgets
    import numpy as np
    import qtpy.QtWidgets


# General types

# PathLike = Union[str, pathlib.Path]  # we really have to pick one
PathLike = str
PathOrPaths = PathLike | Sequence[PathLike]
PythonName = NewType("PythonName", str)

# Layer-related types


class ArrayLike(Protocol):
    @property
    def shape(self) -> tuple[int, ...]: ...

    @property
    def ndim(self) -> int: ...

    @property
    def dtype(self) -> np.dtype: ...

    def __array__(self) -> np.ndarray: ...  # pragma: no cover


LayerName = Literal[
    "graph", "image", "labels", "points", "shapes", "surface", "tracks", "vectors"
]
Metadata = Mapping
DataType = ArrayLike | Sequence[ArrayLike]
FullLayerData = tuple[DataType, Metadata, LayerName]
LayerData = tuple[DataType] | tuple[DataType, Metadata] | FullLayerData

# ########################## CONTRIBUTIONS #################################

# WidgetContribution.command must point to a WidgetCreator
Widget = Union["magicgui.widgets.Widget", "qtpy.QtWidgets.QWidget"]
WidgetCreator = Callable[..., Widget]

# ReaderContribution.command must point to a ReaderGetter
ReaderFunction = Callable[[PathOrPaths], list[LayerData]]
ReaderGetter = Callable[[PathOrPaths], ReaderFunction | None]


# SampleDataGenerator.command must point to a SampleDataCreator
SampleDataCreator = Callable[..., list[LayerData]]

# WriterContribution.command must point to a WriterFunction
# Writers that take at most one layer must provide a SingleWriterFunction command.
# Otherwise, they must provide a MultiWriterFunction.
# where the number of layers they take is defined as
# n = sum(ltc.max() for ltc in WriterContribution.layer_type_constraints())
SingleWriterFunction = Callable[[str, DataType, Metadata], list[str]]
MultiWriterFunction = Callable[[str, list[FullLayerData]], list[str]]
WriterFunction = SingleWriterFunction | MultiWriterFunction

# ##########################################################################
