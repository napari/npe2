from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Union

from npe2._pydantic_compat import Field, GenericModel
from npe2.manifest.utils import Executable
from npe2.types import LayerData

if TYPE_CHECKING:
    from npe2._command_registry import CommandRegistry


class _SampleDataContribution(GenericModel, ABC):
    """Contribute sample data for use in napari.

    Sample data can take the form of a **command** that returns layer data, or a simple
    path or **uri** to a local or remote resource (assuming there is a reader plugin
    capable of reading that path/URI).
    """

    key: str = Field(..., description="A unique key to identify this sample.")
    display_name: str = Field(
        ..., description="String to show in the UI when referring to this sample"
    )

    @abstractmethod
    def open(
        self, *args, _registry: Optional["CommandRegistry"] = None, **kwargs
    ) -> List[LayerData]:
        ...


class SampleDataGenerator(_SampleDataContribution, Executable[List[LayerData]]):
    """Contribute a callable command that creates data on demand."""

    command: str = Field(
        ..., description="Identifier of a command that returns layer data tuple."
    )

    def open(
        self, *args, _registry: Optional["CommandRegistry"] = None, **kwargs
    ) -> List[LayerData]:
        return self.exec(args, kwargs, _registry=_registry)

    class Config:
        title = "Sample Data Function"


class SampleDataURI(_SampleDataContribution):
    """Contribute a URI to static local or remote data. This can be data included in
    the plugin package, or a URL to remote data.  The URI must be readable by either
    napari's builtin reader, or by a plugin that is included/required."""

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
        from npe2.io_utils import read

        return read([self.uri], plugin_name=self.reader_plugin, stack=False)

    class Config:
        title = "Sample Data URI"


SampleDataContribution = Union[SampleDataGenerator, SampleDataURI]
