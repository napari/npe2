from typing import List, Optional

from pydantic import BaseModel

from .commands import CommandContribution

# from .keybindings import KeyBindingContribution
from .menus import MenusContribution
from .readers import ReaderContribution
from .sample_data import SampleDataContribution
from .submenu import SubmenuContribution
from .themes import ThemeContribution
from .widgets import WidgetContribution

# from .configuration import JsonSchemaObject
from .writers import WriterContribution


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    themes: Optional[List[ThemeContribution]]
    readers: Optional[List[ReaderContribution]]
    writers: Optional[List[WriterContribution]]
    sample_data: Optional[List[SampleDataContribution]]
    widgets: Optional[List[WidgetContribution]]

    menus: Optional[MenusContribution]
    submenus: Optional[List[SubmenuContribution]]

    # configuration: Optional[JsonSchemaObject]
    # keybindings: Optional[List[KeyBindingContribution]]
