from typing import List
from enum import Enum
from pydantic import BaseModel, Field, validator


class ReaderContribution(BaseModel):
    command: str = Field(
        ..., description="Identifier of the command providing `napari_get_reader`."
    )
    filename_patterns: List[str] = Field(
        default_factory=list,
        description="List of filename patterns (for fnmatch) that this reader can accept."
        "Reader will be tried only if `fnmatch(filename, pattern) == True`",
    )
    accepts_directories: bool = Field(
        False, description="Whether this reader accepts directories"
    )


class LayerTypes(str, Enum):
    all = "all"
    image = "image"
    labels = "labels"
    points = "points"
    shapes = "shapes"
    vector = "vector"


class WriterContribution(BaseModel):
    command: str = Field(
        ..., description="Identifier of the command providing `napari_get_writer`."
    )
    layer_types: List[LayerTypes] = Field(
        default_factory=lambda: [LayerTypes.all],
        description="List of layer types that this writer can write.",
    )

    filename_extensions: List[str] = Field(
        default_factory=list,
        description="List of filename extensions compatible with this writer.",
    )

    @validator("layer_types")
    def _coerce_layer_type_all(cls, vs: List[str]) -> List[str]:
        """If any of the listed layer types are LayerType.all, replace the 
        list with one of all layer types.
        """
        if LayerTypes.all in vs:
            return list(set(LayerTypes) - set([LayerTypes.all]))
        return vs

    @validator("filename_extensions")
    def _coerce_common_glob_patterns(cls, exts: List[str]) -> List[str]:
        """If any of the listed extensions are common glob patterns, replace the 
        list with one of all extensions.

        Coercions:
        1. File extensions beginning with '*' have their leading '*' removed.
        2. File extensions lacking a leading '.' have a leading '.' added.

        Rules:
        3. File extensions must start with '.' or '*.'
        4. File extensions must be at least two characters long.
        """

        exts = [e if e[0] != "*" else e[1:] for e in exts if len(e) > 1]
        exts = [e if e[0] == "." else f".{e}" for e in exts]

        if not all(e.startswith('.') for e in exts):
            raise ValueError("Invalid file extension: Must start with a period.")

        if any(len(e) < 2 for e in exts):
            raise ValueError(
                "Invalid file extension: Must have one character past the '.'"
            )
        return exts

