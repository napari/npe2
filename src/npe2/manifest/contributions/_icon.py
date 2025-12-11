from npe2._pydantic_compat import BaseModel


class Icon(BaseModel):
    light: str | None = None
    dark: str | None = None
