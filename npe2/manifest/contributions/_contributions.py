from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from ._commands import CommandContribution
from ._menus import MenuContribution, NAPARI_MENUS
from ._readers import ReaderContribution
from ._sample_data import SampleDataContribution
from ._submenu import SubmenuContribution
from ._themes import ThemeContribution
from ._widgets import WidgetContribution
from ._writers import WriterContribution


VALID_MENUS_NAMES = {n.key for n in NAPARI_MENUS}


class ContributionPoints(BaseModel):
    commands: Optional[List[CommandContribution]]
    readers: Optional[List[ReaderContribution]]
    writers: Optional[List[WriterContribution]]
    widgets: Optional[List[WidgetContribution]]
    sample_data: Optional[List[SampleDataContribution]]
    themes: Optional[List[ThemeContribution]]

    # We use a dict for menus to allow for keys with `/`
    menus: Optional[MenuContribution] = Field(None, hide_docs=True)
    submenus: Optional[List[SubmenuContribution]] = Field(None, hide_docs=True)

    # configuration: Optional[JsonSchemaObject]
    # keybindings: Optional[List[KeyBindingContribution]]

    @validator("menus")
    def _check_napari_menus(cls, v):
        for key in v.keys():
            if key not in VALID_MENUS_NAMES:
                raise ValueError(
                    f"Menu location not recognized. Got {key},"
                    f" valid locations are {VALID_MENUS_NAMES}."
                )
        return v

    class Config:
        docs_exclude = {"menus", "submenus"}
