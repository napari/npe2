from pydantic import Field

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
    mac: str | None = Field(description="Mac specific key or key sequence.")
    linux: str | None = Field(description="Linux specific key or key sequence.")
    win: str | None = Field(description="Windows specific key or key sequence.")
    when: str | None = Field(description="Condition when the key is active.")
