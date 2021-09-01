from typing import List, Optional

from datamodel_code_generator.parser.jsonschema import JsonSchemaObject
from pydantic import BaseModel

from .commands import CommandContribution
from .keybindings import KeyBindingContribution
from .menus import MenusContribution
from .submenu import SubmenuContribution
from .themes import ThemeContribution
from .io import ReaderContribution


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    configuration: Optional[JsonSchemaObject]
    keybindings: Optional[List[KeyBindingContribution]]
    menus: Optional[MenusContribution]
    submenus: Optional[List[SubmenuContribution]]
    themes: Optional[List[ThemeContribution]]
    readers: Optional[List[ReaderContribution]]
