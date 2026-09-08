import json
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import yaml
from pydantic import BaseModel, PrivateAttr


class _UniqueKeyYamlLoader(yaml.SafeLoader):
    """YAML loader that raises on duplicate keys within a single mapping.

    PyYAML (like the stdlib `json` module) silently keeps the *last* value
    for a duplicate key within a mapping, which would let e.g. two
    `contributions.configurations` entries share a key and silently
    discard one during parsing -- before pydantic ever sees the data to
    validate it. This loader catches that at parse time instead.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _load_yaml_no_duplicates(stream):
    return yaml.load(stream, Loader=_UniqueKeyYamlLoader)


def _no_duplicate_keys_object_pairs_hook(pairs):
    """`object_pairs_hook` for `json.load` that rejects duplicate object keys.

    See `_UniqueKeyYamlLoader` for why: the stdlib `json` module otherwise
    silently keeps the last value for a duplicate key.
    """
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"Duplicate key {key!r} found while parsing JSON.")
        seen[key] = value
    return seen


def _load_json_no_duplicates(stream):
    return json.load(stream, object_pairs_hook=_no_duplicate_keys_object_pairs_hook)


class ImportExportModel(BaseModel):
    """Model mixin/base class that provides read/write from toml/yaml/json.

    To force the inclusion of a given field in the exported toml/yaml use:

        class MyModel(ImportExportModel):
            some_field: str = Field(..., always_export=True)
    """

    _source_file: Path | None = PrivateAttr(None)

    def toml(self, pyproject=False, **kwargs) -> str:
        """Generate serialized `toml` string for this model.

        Parameters
        ----------
        pyproject : bool, optional
            If `True`, output will be in pyproject format, with all data under
            `tool.napari`, by default `False`.
        **kwargs
            passed to `BaseModel.model_dump_json()`
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
            passed to `BaseModel.model_dump_json()`
        """
        return yaml.safe_dump(self._serialized_data(**kwargs), sort_keys=False)

    @classmethod
    def from_file(cls, path: Path | str):
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
            loader = _load_json_no_duplicates
        elif path.suffix.lower() == ".toml":
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore [no-redef]

            loader = tomllib.load
        elif path.suffix.lower() in (".yaml", ".yml"):
            loader = _load_yaml_no_duplicates
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
            return json.loads(self.model_dump_json(**kwargs))

    @contextmanager
    def _required_export_fields_set(self):
        field_schemas = self.model_json_schema()["properties"]
        required = {
            k for k, v in field_schemas.items() if v.get("always_export", False)
        }

        was_there: dict[str, bool] = {}
        for f in required:
            was_there[f] = f in self.model_fields_set
            self.model_fields_set.add(f)
        try:
            yield
        finally:
            for f in required:
                if not was_there.get(f):
                    self.model_fields_set.discard(f)
