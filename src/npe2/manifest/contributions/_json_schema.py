from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type, Union

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
    "ValidationError",
    "Draft04JsonSchema",
    "Draft06JsonSchema",
    "Draft07JsonSchema",
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


def _to_json_type(type_: Union[str, Type]) -> JsonType:
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

_python_equivalent: Dict[Optional[str], Type] = {
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
    schema_: Optional[str] = Field(None, alias="$schema")
    title: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    default: Any = Field(None)
    multiple_of: Optional[float] = Field(None, ge=0)
    maximum: Optional[float] = Field(None)
    minimum: Optional[float] = Field(None)
    max_length: Optional[int] = Field(None, ge=0)
    min_length: Optional[int] = Field(0, ge=0)
    # could be Pattern. but it's easier to work with as str
    pattern: Optional[str] = Field(None)
    max_items: Optional[int] = Field(None, ge=0)
    min_items: Optional[int] = Field(0, ge=0)
    unique_items: bool = Field(False)
    max_properties: Optional[int] = Field(None, ge=0)
    min_properties: Optional[int] = Field(0, ge=0)
    enum: Optional[conlist(Any, min_items=1, unique_items=True)] = Field(None)  # type: ignore  # noqa
    type: Union[JsonType, JsonTypeArray] = Field(None)  # type: ignore
    format: Optional[str] = Field(None)

    _json_validator: Type[Validator] = PrivateAttr()

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
    def _validate_root(cls, values: Dict[str, Any]) -> Any:
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
    def python_type(self) -> Union[Type, List[Type]]:
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
        return (
            self.properties is not None
            or self.type == "object"
            and not self.all_of
            and not self.one_of
            and not self.any_of
            and not getattr(self, "ref", False)  # draft 6+
        )

    @property
    def json_validator(self) -> Type[Validator]:
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
    id: Optional[str] = Field(None)
    exclusive_maximum: Optional[bool] = Field(None)
    exclusive_minimum: Optional[bool] = Field(None)
    required: Optional[StringArrayMin1] = Field(None)  # type: ignore
    dependencies: Optional[  # type: ignore
        Dict[str, Union[Draft04JsonSchema, StringArrayMin1]]
    ] = Field(None)

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    additional_items: Union[bool, Draft04JsonSchema, None] = Field(None)
    items: Union[Draft04JsonSchema, List[Draft04JsonSchema], None] = Field(None)
    additional_properties: Union[bool, Draft04JsonSchema, None] = Field(None)
    definitions: Optional[Dict[str, Draft04JsonSchema]] = Field(None)
    properties: Optional[Dict[str, Draft04JsonSchema]] = Field(None)
    pattern_properties: Optional[Dict[str, Draft04JsonSchema]] = Field(None)
    all_of: Optional[List[Draft04JsonSchema]] = Field(None)
    any_of: Optional[List[Draft04JsonSchema]] = Field(None)
    one_of: Optional[List[Draft04JsonSchema]] = Field(None)
    not_: Optional[Draft04JsonSchema] = Field(None, alias="not")


class _Draft06JsonSchema(_JsonSchemaBase):
    id: Optional[str] = Field(None, alias="$id")
    # ref: Optional[str] = Field(None, alias="$ref")
    examples: Optional[List[Any]] = Field(None)
    exclusive_maximum: Optional[float] = Field(None)
    exclusive_minimum: Optional[float] = Field(None)
    contains: Optional[Draft06JsonSchema] = Field(None)
    required: Optional[StringArray] = Field(None)  # type: ignore
    dependencies: Optional[  # type: ignore
        Dict[str, Union[Draft06JsonSchema, StringArray]]
    ] = Field(None)
    property_names: Optional[Draft06JsonSchema] = Field(None)
    const: Any = Field(None)


class Draft06JsonSchema(_Draft06JsonSchema):
    """Model for Draft 6 JSON Schema."""

    schema_: str = Field("http://json-schema.org/draft-06/schema#", alias="$schema")

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    # and... technically, all subschemas may also be booleans as of Draft 6,
    # not just additional_properties and additional_items
    additional_items: Union[bool, Draft06JsonSchema, None] = Field(None)
    items: Union[Draft06JsonSchema, List[Draft06JsonSchema], None] = Field(None)
    additional_properties: Union[bool, Draft06JsonSchema, None] = Field(None)
    # definitions: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    properties: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    pattern_properties: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    all_of: Optional[List[Draft06JsonSchema]] = Field(None)
    any_of: Optional[List[Draft06JsonSchema]] = Field(None)
    one_of: Optional[List[Draft06JsonSchema]] = Field(None)
    not_: Optional[Draft06JsonSchema] = Field(None, alias="not")


class Draft07JsonSchema(_Draft06JsonSchema):
    """Model for Draft 7 JSON Schema."""

    schema_: str = Field("http://json-schema.org/draft-07/schema#", alias="$schema")
    comment: Optional[str] = Field(None, alias="$comment")
    read_only: bool = Field(False)
    write_only: bool = Field(False)
    content_media_type: Optional[str] = Field(None)
    content_encoding: Optional[str] = Field(None)
    if_: Optional[Draft07JsonSchema] = Field(None, alias="if")
    then: Optional[Draft07JsonSchema] = Field(None)
    else_: Optional[Draft07JsonSchema] = Field(None, alias="else")

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    # and... technically, all subschemas may also be booleans as of Draft 6,
    # not just additional_properties and additional_items
    additional_items: Union[bool, Draft07JsonSchema, None] = Field(None)
    items: Union[Draft07JsonSchema, List[Draft07JsonSchema], None] = Field(None)
    additional_properties: Union[bool, Draft07JsonSchema, None] = Field(None)
    # definitions: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    properties: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    pattern_properties: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    all_of: Optional[List[Draft07JsonSchema]] = Field(None)
    any_of: Optional[List[Draft07JsonSchema]] = Field(None)
    one_of: Optional[List[Draft07JsonSchema]] = Field(None)
    not_: Optional[Draft07JsonSchema] = Field(None, alias="not")
