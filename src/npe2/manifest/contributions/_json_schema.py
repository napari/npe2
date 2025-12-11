from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from npe2._pydantic_compat import (
    BaseModel,
    Field,
    PrivateAttr,
    conlist,
    root_validator,
    validator,
)

if TYPE_CHECKING:
    from jsonschema.exceptions import ValidationError
    from jsonschema.protocols import Validator
else:
    try:
        from jsonschema.exceptions import ValidationError
    except ImportError:
        ValidationError = Exception

__all__ = [
    "Draft04JsonSchema",
    "Draft06JsonSchema",
    "Draft07JsonSchema",
    "ValidationError",
]

JsonType = Literal["array", "boolean", "integer", "null", "number", "object", "string"]
JsonTypeArray = conlist(JsonType, min_items=1, unique_items=True)
StringArrayMin1 = conlist(str, min_items=1, unique_items=True)
StringArray = conlist(str, unique_items=True)

PY_NAME_TO_JSON_NAME = {
    "list": "array",
    "bool": "boolean",
    "int": "integer",
    "float": "number",
    "dict": "object",
    "str": "string",
    "NoneType": "null",
    "None": "null",
}


def _to_json_type(type_: str | type) -> JsonType:
    if isinstance(type_, type):
        type_ = type_.__name__
    type_ = str(type_).lower()
    return PY_NAME_TO_JSON_NAME.get(type_, type_)  # type: ignore # (validated later)


def _coerce_type_name(v):
    """Coerce python type names to json schema type names."""
    if isinstance(v, list):
        return [_to_json_type(t) for t in v]
    return _to_json_type(v)


def _to_camel(string: str) -> str:
    words = string.split("_")
    return words[0] + "".join(w.capitalize() for w in words[1:])


_CONSTRAINT_FIELDS = {
    "exclusive_minimum",
    "minimum",
    "exclusive_maximum",
    "maximum",
    "multiple_of",
    "min_items",
    "max_items",
    "min_length",
    "max_length",
    "pattern",
}

_python_equivalent: dict[str | None, type] = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "null": type(None),
    "number": float,
    "object": dict,
    "string": str,
    None: object,
}


class _JsonSchemaBase(BaseModel):
    class Config:
        alias_generator = _to_camel
        allow_population_by_field_name = True

    # underscore here to avoid name collision with pydantic's `schema` method
    schema_: str | None = Field(None, alias="$schema")
    title: str | None = Field(None)
    description: str | None = Field(None)
    default: Any = Field(None)
    multiple_of: float | None = Field(None, ge=0)
    maximum: float | None = Field(None)
    minimum: float | None = Field(None)
    max_length: int | None = Field(None, ge=0)
    min_length: int | None = Field(0, ge=0)
    # could be Pattern. but it's easier to work with as str
    pattern: str | None = Field(None)
    max_items: int | None = Field(None, ge=0)
    min_items: int | None = Field(0, ge=0)
    unique_items: bool = Field(False)
    max_properties: int | None = Field(None, ge=0)
    min_properties: int | None = Field(0, ge=0)
    enum: conlist(Any, min_items=1, unique_items=True) | None = Field(None)  # type: ignore
    type: JsonType | JsonTypeArray = Field(None)  # type: ignore
    format: str | None = Field(None)

    _json_validator: builtins.type[Validator] = PrivateAttr()

    # these will be redefined in subclasses with specific subschema types
    # just here for type-checking in the methods of this base class
    if TYPE_CHECKING:
        items: Any
        properties: Any
        all_of: Any
        any_of: Any
        one_of: Any

    _coerce_type_name = validator("type", pre=True, allow_reuse=True)(_coerce_type_name)

    @root_validator(pre=True)
    def _validate_root(cls, values: dict[str, Any]) -> Any:
        if "type" not in values:
            if "properties" in values:
                values["type"] = "object"
            elif "items" in values:
                values["type"] = "array"

        # Get around pydantic bug wherein `Optional[conlists]`` throw a
        # 'NoneType' object is not iterable error if `None` is provided in init.
        for conlists in ("enum", "required"):
            if conlists in values and not values[conlists]:
                values.pop(conlists)

        return values

    @property
    def has_constraint(self) -> bool:
        """Return True if this schema has any constraints."""
        return bool(_CONSTRAINT_FIELDS & self.__fields_set__)

    @property
    def has_default(self) -> bool:
        """Return True if the schema has a default value."""
        return "default" in self.__fields_set__

    @property
    def python_type(self) -> builtins.type | list[builtins.type]:
        """Return Python type equivalent(s) for this schema (JSON) type."""
        if isinstance(self.type, list):
            return [_python_equivalent[t] for t in self.type]
        else:
            return _python_equivalent[self.type]

    @property
    def is_array(self) -> bool:
        """Return True if this schema is an array schema."""
        return self.items is not None or self.type == "array"

    @property
    def is_object(self) -> bool:
        """Return True if this schema is an object schema."""
        return self.properties is not None or (
            self.type == "object"
            and not self.all_of
            and not self.one_of
            and not self.any_of
            and not getattr(self, "ref", False)
        )  # draft 6+

    @property
    def json_validator(self) -> builtins.type[Validator]:
        """Return jsonschema validator class for this schema.

        See also `validate_instance`.
        """
        if not hasattr(self, "_json_validator"):
            from jsonschema.validators import validator_for

            schema = self.dict(by_alias=True, exclude_unset=True)
            schema["$schema"] = self.schema_
            cls = validator_for(schema)
            cls.check_schema(schema)
            self._json_validator = cls(schema)
        return self._json_validator

    def validate_instance(self, instance: Any) -> dict:
        """Validate an object (instance) against this schema."""
        from jsonschema.exceptions import best_match

        error: ValidationError = best_match(self.json_validator.iter_errors(instance))
        if error is not None:
            raise error
        return instance


class Draft04JsonSchema(_JsonSchemaBase):
    """Model for Draft 4 JSON Schema."""

    schema_: str = Field("http://json-schema.org/draft-04/schema#", alias="$schema")
    id: str | None = Field(None)
    exclusive_maximum: bool | None = Field(None)
    exclusive_minimum: bool | None = Field(None)
    required: StringArrayMin1 | None = Field(None)  # type: ignore
    dependencies: dict[str, Draft04JsonSchema | StringArrayMin1] | None = Field(None)  # type: ignore

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    additional_items: bool | Draft04JsonSchema | None = Field(None)
    items: Draft04JsonSchema | list[Draft04JsonSchema] | None = Field(None)
    additional_properties: bool | Draft04JsonSchema | None = Field(None)
    definitions: dict[str, Draft04JsonSchema] | None = Field(None)
    properties: dict[str, Draft04JsonSchema] | None = Field(None)
    pattern_properties: dict[str, Draft04JsonSchema] | None = Field(None)
    all_of: list[Draft04JsonSchema] | None = Field(None)
    any_of: list[Draft04JsonSchema] | None = Field(None)
    one_of: list[Draft04JsonSchema] | None = Field(None)
    not_: Draft04JsonSchema | None = Field(None, alias="not")


class _Draft06JsonSchema(_JsonSchemaBase):
    id: str | None = Field(None, alias="$id")
    # ref: Optional[str] = Field(None, alias="$ref")
    examples: list[Any] | None = Field(None)
    exclusive_maximum: float | None = Field(None)
    exclusive_minimum: float | None = Field(None)
    contains: Draft06JsonSchema | None = Field(None)
    required: StringArray | None = Field(None)  # type: ignore
    dependencies: dict[str, Draft06JsonSchema | StringArray] | None = Field(None)  # type: ignore
    property_names: Draft06JsonSchema | None = Field(None)
    const: Any = Field(None)


class Draft06JsonSchema(_Draft06JsonSchema):
    """Model for Draft 6 JSON Schema."""

    schema_: str = Field("http://json-schema.org/draft-06/schema#", alias="$schema")

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    # and... technically, all subschemas may also be booleans as of Draft 6,
    # not just additional_properties and additional_items
    additional_items: bool | Draft06JsonSchema | None = Field(None)
    items: Draft06JsonSchema | list[Draft06JsonSchema] | None = Field(None)
    additional_properties: bool | Draft06JsonSchema | None = Field(None)
    # definitions: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    properties: dict[str, Draft06JsonSchema] | None = Field(None)
    pattern_properties: dict[str, Draft06JsonSchema] | None = Field(None)
    all_of: list[Draft06JsonSchema] | None = Field(None)
    any_of: list[Draft06JsonSchema] | None = Field(None)
    one_of: list[Draft06JsonSchema] | None = Field(None)
    not_: Draft06JsonSchema | None = Field(None, alias="not")


class Draft07JsonSchema(_Draft06JsonSchema):
    """Model for Draft 7 JSON Schema."""

    schema_: str = Field("http://json-schema.org/draft-07/schema#", alias="$schema")
    comment: str | None = Field(None, alias="$comment")
    read_only: bool = Field(False)
    write_only: bool = Field(False)
    content_media_type: str | None = Field(None)
    content_encoding: str | None = Field(None)
    if_: Draft07JsonSchema | None = Field(None, alias="if")
    then: Draft07JsonSchema | None = Field(None)
    else_: Draft07JsonSchema | None = Field(None, alias="else")

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    # and... technically, all subschemas may also be booleans as of Draft 6,
    # not just additional_properties and additional_items
    additional_items: bool | Draft07JsonSchema | None = Field(None)
    items: Draft07JsonSchema | list[Draft07JsonSchema] | None = Field(None)
    additional_properties: bool | Draft07JsonSchema | None = Field(None)
    # definitions: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    properties: dict[str, Draft07JsonSchema] | None = Field(None)
    pattern_properties: dict[str, Draft07JsonSchema] | None = Field(None)
    all_of: list[Draft07JsonSchema] | None = Field(None)
    any_of: list[Draft07JsonSchema] | None = Field(None)
    one_of: list[Draft07JsonSchema] | None = Field(None)
    not_: Draft07JsonSchema | None = Field(None, alias="not")
