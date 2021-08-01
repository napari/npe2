from typing import List, Optional

from pydantic import BaseModel

from .commands import CommandContribution
from .keybindings import KeyBindingContribution
from .menus import MenusContribution
from .submenu import SubmenuContribution


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    menus: Optional[MenusContribution]
    keybindings: Optional[List[KeyBindingContribution]]
    submenus: Optional[List[SubmenuContribution]]
