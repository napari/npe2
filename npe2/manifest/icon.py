from typing import Optional

from pydantic import BaseModel


class Icon(BaseModel):
    light: Optional[str]
    dark: Optional[str]
