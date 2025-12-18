from pydantic import BaseModel


class Icon(BaseModel):
    light: str | None = None
    dark: str | None = None
