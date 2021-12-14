from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Tuple, Union

from typing_extensions import Literal, Protocol

if TYPE_CHECKING:
    import magicgui.widgets
    import numpy as np
    import qtpy.QtWidgets


# General types

PathLike = Union[str, Path]
PathOrPaths = Union[PathLike, Sequence[PathLike]]


# Layer-related types


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

# ########################## CONTRIBUTIONS #################################

# WidgetContribution.command must point to a WidgetCreator
Widget = Union["magicgui.widgets.Widget", "qtpy.QtWidgets.QWidget"]
WidgetCreator = Callable[..., Widget]

# ReaderContribution.command must point to a ReaderGetter
ReaderFunction = Callable[[PathOrPaths], List[LayerData]]
ReaderGetter = Callable[[Union[str, List[str]]], Optional[ReaderFunction]]

# SampleDataGenerator.command must point to a SampleDataCreator
SampleDataCreator = Callable[..., List[LayerData]]

# WriterContribution.command must point to a WriterFunction.
# Currently, two calling conventions are supported for writers: single-layer and
# multi-layer writers. When at most one layer can be matched by a writer, it
# must use the single-layer convention. Otherwise, the multi-layer convention
# must be used. WriterFunctions are only called when the set of layers to be
# written satisfies a set of layer-type constraints specified by
# WriterContribution.layer_types.layer_type_constraints().
SingleWriterFunction = Callable[[str, DataType, Metadata], List[str]]
MultiWriterFunction = Callable[[str, List[FullLayerData]], List[str]]
WriterFunction = Union[SingleWriterFunction, MultiWriterFunction]

# ##########################################################################
