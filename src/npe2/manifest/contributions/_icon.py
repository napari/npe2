from typing import Optional

from npe2._pydantic_compat import BaseModel


class Icon(BaseModel):
    light: Optional[str] = None
    dark: Optional[str] = None
