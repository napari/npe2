from typing import Optional

from pydantic import BaseModel
from pydantic.fields import Field

from .utils import Executable


# the existence of the command is not validated at registration-time,
# but rather at call time... (since commands from other extensions can be called)
class KeyBindingContribution(BaseModel, Executable):
    command: str = Field(
        description="Identifier of the command to run when keybinding is triggered."
    )
    key: str = Field(
        description="Key or key sequence (separate keys with plus-sign and sequences "
        "with space, e.g. Ctrl+O and Ctrl+L L for a chord)."
    )
    mac: Optional[str] = Field(description="Mac specific key or key sequence.")
    linux: Optional[str] = Field(description="Linux specific key or key sequence.")
    win: Optional[str] = Field(description="Windows specific key or key sequence.")
    when: Optional[str] = Field(description="Condition when the key is active.")
