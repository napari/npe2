from pydantic import BaseModel
from typing import Optional


class Icon(BaseModel):
    light: Optional[str]
    dark: Optional[str]
