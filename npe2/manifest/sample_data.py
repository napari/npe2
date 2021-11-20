from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel
from pydantic.fields import Field

from .._types import LayerData
from .utils import Executable

if TYPE_CHECKING:
    from .._command_registry import CommandRegistry


class _SampleDataContribution(BaseModel, ABC):
    display_name: str = Field(
        ..., description="String to show in the GUI when refering to this sample"
    )
    key: str = Field(
        ...,
        description="A key to identify this sample. Must be unique across the various "
        "samples provided by a single plugin",
    )

    @abstractmethod
    def open(
        self, *args, _registry: Optional["CommandRegistry"] = None, **kwargs
    ) -> List[LayerData]:
        ...


class SampleDataGenerator(_SampleDataContribution, Executable[List[LayerData]]):
    command: str = Field(
        ..., description="Identifier of a command that returns layer data tuple."
    )

    def open(
        self, *args, _registry: Optional["CommandRegistry"] = None, **kwargs
    ) -> List[LayerData]:
        return self.exec(args, kwargs, _registry=_registry)


class SampleDataURI(_SampleDataContribution):
    uri: str = Field(
        ...,
        description="Path or URL to a data resource. "
        "This URI should be a valid input to `io_utils.read`",
    )
    reader_plugin: Optional[str] = Field(
        None,
        description="Name of plugin to use to open URI",
    )

    def open(self, *args, **kwargs) -> List[LayerData]:
        from ..io_utils import read

        return read(self.uri, plugin_name=self.reader_plugin)


SampleDataContribution = Union[SampleDataGenerator, SampleDataURI]
