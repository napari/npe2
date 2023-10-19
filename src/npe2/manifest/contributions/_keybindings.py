from typing import Optional

from npe2._pydantic_compat import Field
from npe2.manifest.utils import Executable


class KeyBindingContribution(Executable):
    command: str = Field(
        description="Identifier of the command to run when keybinding is triggered."
    )
    # the existence of the command is not validated at registration-time,
    # but rather at call time... (since commands from other extensions can be called)
    key: str = Field(
        description="Key or key sequence (separate simultaneous key presses with "
        "a plus-sign e.g. Ctrl+O and sequences with a space e.g. Ctrl+L L for a chord)."
    )
    mac: Optional[str] = Field(description="Mac specific key or key sequence.")
    linux: Optional[str] = Field(description="Linux specific key or key sequence.")
    win: Optional[str] = Field(description="Windows specific key or key sequence.")
    when: Optional[str] = Field(description="Condition when the key is active.")
