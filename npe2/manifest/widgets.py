from pydantic import BaseModel, Extra, Field

from .._types import Widget
from .utils import Executable


class WidgetContribution(BaseModel, Executable[Widget]):
    command: str = Field(
        ..., description="Identifier of a command that returns a Widget instance."
    )
    name: str

    class Config:
        extra = Extra.forbid
