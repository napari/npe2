import json
from pathlib import Path
from typing import Callable, Type, TypeVar, Union

import pytomlpp as toml
import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ImportExportMixin:
    """Mixin that provides read/write from toml/yaml/json."""

    def toml(self: BaseModel, pyproject=False) -> str:
        d = json.loads(self.json(exclude_unset=True))
        if pyproject:
            d = {"tool": {"napari": d}}
        return toml.dumps(d)

    def yaml(self: BaseModel) -> str:
        return yaml.safe_dump(
            json.loads(self.json(exclude_unset=True)), sort_keys=False
        )

    @classmethod
    def from_file(cls: Type[T], path: Union[Path, str]) -> T:

        path = Path(path).expanduser().absolute().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        loader: Callable
        if path.suffix.lower() == ".json":
            loader = json.load
        elif path.suffix.lower() == ".toml":
            loader = toml.load
        elif path.suffix.lower() in (".yaml", ".yml"):
            loader = yaml.safe_load
        else:
            raise ValueError(f"unrecognized file extension: {path}")

        with open(path) as f:
            data = loader(f) or {}

        if path.name == "pyproject.toml":
            data = data["tool"]["napari"]

        return cls(**data)
