from functools import wraps
from typing import List, Optional

from npe2._pydantic_compat import Extra, Field
from npe2.manifest.utils import Executable, v2_to_v1
from npe2.types import ReaderFunction


class ReaderContribution(Executable[Optional[ReaderFunction]]):
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

    def exec(self, *, kwargs):
        """
        We are trying to simplify internal npe2 logic to always deal with a
        (list[str], bool) pair instead of Union[PathLike, Seq[Pathlike]]. We
        thus wrap the Reader Contributions to still give them the old api. Later
        on we could add a "if manifest.version == 2" or similar to not have this
        backward-compatibility logic for new plugins.
        """
        kwargs = kwargs.copy()
        stack = kwargs.pop("stack", None)
        assert stack is not None
        kwargs["path"] = v2_to_v1(kwargs["path"], stack)
        callable_ = super().exec(kwargs=kwargs)

        if callable_ is None:  # pragma: no cover
            return None

        @wraps(callable_)
        def npe1_compat(paths, *, stack):
            path = v2_to_v1(paths, stack)
            return callable_(path)

        return npe1_compat
