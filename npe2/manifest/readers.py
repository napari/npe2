from typing import List, Optional

from pydantic import BaseModel, Extra, Field

from ..types import ReaderFunction
from .utils import Executable


class ReaderContribution(BaseModel, Executable[Optional[ReaderFunction]]):
    """Contribute a file reader.

    Readers may be associated with specific **filename_patterns** (e.g. "*.tif",
    "*.zip") and are invoked whenever `viewer.open('some/path')` is used on the
    command line, or when a user opens a file in the graphical user interface by
    dropping a file into the canvas, or using `File -> Open...`
    """

    command: str = Field(
        ..., description="Identifier of the command providing `napari_get_reader`."
    )
    filename_patterns: List[str] = Field(
        ...,
        description="List of filename patterns (for fnmatch) that this reader can "
        "accept. Reader will be tried only if `fnmatch(filename, pattern) == True`. "
        "Use `['*']` to match all filenames.",
    )
    accepts_directories: bool = Field(
        False, description="Whether this reader accepts directories"
    )

    class Config:
        extra = Extra.forbid

    def __hash__(self):
        return hash(
            (self.command, tuple(self.filename_patterns), self.accepts_directories)
        )
