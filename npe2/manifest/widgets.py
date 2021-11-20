from pydantic import BaseModel, Extra, Field

from .._types import WidgetCallable
from .utils import Executable


class WidgetContribution(BaseModel, Executable[WidgetCallable]):
    command: str = Field(
        ..., description="Identifier of a command that returns a Widget instance."
    )
    name: str

    class Config:
        extra = Extra.forbid
