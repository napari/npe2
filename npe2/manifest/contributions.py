from typing import List, Optional

from pydantic import BaseModel

from .commands import CommandContribution

# from .configuration import JsonSchemaObject
from .io import ReaderContribution, WriterContribution

# from .keybindings import KeyBindingContribution
from .menus import MenusContribution
from .sample_data import SampleDataContribution
from .submenu import SubmenuContribution
from .themes import ThemeContribution
from .widgets import WidgetContribution


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    readers: Optional[List[ReaderContribution]]
    writers: Optional[List[WriterContribution]]
    widgets: Optional[List[WidgetContribution]]
    sample_data: Optional[List[SampleDataContribution]]
    themes: Optional[List[ThemeContribution]]

    menus: Optional[MenusContribution]
    submenus: Optional[List[SubmenuContribution]]

    # configuration: Optional[JsonSchemaObject]
    # keybindings: Optional[List[KeyBindingContribution]]

    class Config:
        docs_exclude = {"menus", "submenus"}
