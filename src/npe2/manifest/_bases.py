import json
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import yaml

from npe2._pydantic_compat import BaseModel, PrivateAttr


class ImportExportModel(BaseModel):
    """Model mixin/base class that provides read/write from toml/yaml/json.

    To force the inclusion of a given field in the exported toml/yaml use:

        class MyModel(ImportExportModel):
            some_field: str = Field(..., always_export=True)
    """

    _source_file: Optional[Path] = PrivateAttr(None)

    def toml(self, pyproject=False, **kwargs) -> str:
        """Generate serialized `toml` string for this model.

        Parameters
        ----------
        pyproject : bool, optional
            If `True`, output will be in pyproject format, with all data under
            `tool.napari`, by default `False`.
        **kwargs
            passed to `BaseModel.json()`
        """
        import tomli_w

        d = self._serialized_data(**kwargs)
        if pyproject:
            d = {"tool": {"napari": d}}
        return tomli_w.dumps(d)

    def yaml(self, **kwargs) -> str:
        """Generate serialized `yaml` string for this model.

        Parameters
        ----------
        **kwargs
            passed to `BaseModel.json()`
        """
        return yaml.safe_dump(self._serialized_data(**kwargs), sort_keys=False)

    @classmethod
    def from_file(cls, path: Union[Path, str]):
        """Parse model from a metadata file.

        Parameters
        ----------
        path : Path or str
            Path to file.  Must have extension {'.json', '.yaml', '.yml', '.toml'}

        Returns
        -------
        object
            The parsed model.

        Raises
        ------
        FileNotFoundError
            If `path` does not exist.
        ValueError
            If the file extension is not in {'.json', '.yaml', '.yml', '.toml'}
        """
        path = Path(path).expanduser().absolute().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        loader: Callable
        if path.suffix.lower() == ".json":
            loader = json.load
        elif path.suffix.lower() == ".toml":
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore [no-redef]

            loader = tomllib.load
        elif path.suffix.lower() in (".yaml", ".yml"):
            loader = yaml.safe_load
        else:
            raise ValueError(f"unrecognized file extension: {path}")  # pragma: no cover

        with open(path, mode="rb") as f:
            data = loader(f) or {}

        if path.name == "pyproject.toml":
            data = data["tool"]["napari"]

        obj = cls(**data)
        obj._source_file = Path(path).expanduser().absolute().resolve()
        return obj

    def _serialized_data(self, **kwargs):
        """using json encoders for all outputs"""
        kwargs.setdefault("exclude_unset", True)
        with self._required_export_fields_set():
            return json.loads(self.json(**kwargs))

    @contextmanager
    def _required_export_fields_set(self):
        fields = self.__fields__.items()
        required = {k for k, v in fields if v.field_info.extra.get("always_export")}

        was_there: Dict[str, bool] = {}
        for f in required:
            was_there[f] = f in self.__fields_set__
            self.__fields_set__.add(f)
        try:
            yield
        finally:
            for f in required:
                if not was_there.get(f):
                    self.__fields_set__.discard(f)
