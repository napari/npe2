from typing import List, Optional

from pydantic import BaseModel

from .commands import CommandContribution
from .configuration import JsonSchemaObject
from .io import ReaderContribution, WriterContribution
from .keybindings import KeyBindingContribution
from .menus import MenusContribution
from .submenu import SubmenuContribution
from .themes import ThemeContribution
from .widgets import WidgetContribution


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    configuration: Optional[JsonSchemaObject]
    keybindings: Optional[List[KeyBindingContribution]]
    menus: Optional[MenusContribution]
    submenus: Optional[List[SubmenuContribution]]
    themes: Optional[List[ThemeContribution]]
    readers: Optional[List[ReaderContribution]]
    writers: Optional[List[WriterContribution]]
    widgets: Optional[List[WidgetContribution]]
