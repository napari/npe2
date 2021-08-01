from typing import Literal, Union

from pydantic import BaseModel


class OnExtensionEvent(BaseModel):
    # This activation event is emitted and interested extensions will be
    # activated whenever a file that resolves to a certain language gets opened
    # eg: on_extention:tiff
    kind: Literal["on_extension"]
    id: str


class OnCommandEvent(BaseModel):
    # This activation event is emitted and interested extensions will be
    # activated whenever a command is being invoked:
    # eg: on_command:extension.sayHello
    kind: Literal["on_command"]
    id: str


AfterStartupEvent = Literal["after_startup"]

ActivationEvent = Union[AfterStartupEvent, OnCommandEvent, OnExtensionEvent]
