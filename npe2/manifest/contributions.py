from typing import List, Optional

from pydantic import BaseModel, Field

from .commands import CommandContribution
from .menus import MenusContribution
from .readers import ReaderContribution
from .sample_data import SampleDataContribution, SampleDataGenerator, SampleDataURI
from .submenu import SubmenuContribution
from .themes import ThemeContribution
from .widgets import WidgetContribution
from .writers import WriterContribution

__all__ = [
    "ContributionPoints",
    "CommandContribution",
    "MenusContribution",
    "ReaderContribution",
    "SampleDataContribution",
    "SubmenuContribution",
    "ThemeContribution",
    "WidgetContribution",
    "WriterContribution",
    "SampleDataGenerator",
    "SampleDataURI",
]


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    readers: Optional[List[ReaderContribution]]
    writers: Optional[List[WriterContribution]]
    widgets: Optional[List[WidgetContribution]]
    sample_data: Optional[List[SampleDataContribution]]
    themes: Optional[List[ThemeContribution]]

    menus: Optional[MenusContribution] = Field(None, hide_docs=True)
    submenus: Optional[List[SubmenuContribution]] = Field(None, hide_docs=True)

    # configuration: Optional[JsonSchemaObject]
    # keybindings: Optional[List[KeyBindingContribution]]

    class Config:
        docs_exclude = {"menus", "submenus"}
