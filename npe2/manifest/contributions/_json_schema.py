from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Type,
    Union,
)

from pydantic import BaseModel, Field, conlist, root_validator

JsonType = Literal["array", "boolean", "integer", "null", "number", "object", "string"]
JsonTypeArray = conlist(JsonType, min_items=True, unique_items=True)
StringArrayMin1 = conlist(str, unique_items=True, min_items=1)
StringArray = conlist(str, unique_items=True)


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
    class Config:  # noqa: D106
        alias_generator = _to_camel

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
    pattern: Optional[Pattern] = Field(None)
    max_items: Optional[int] = Field(None, ge=0)
    min_items: Optional[int] = Field(0, ge=0)
    unique_items: bool = Field(False)
    max_properties: Optional[int] = Field(None, ge=0)
    min_properties: Optional[int] = Field(0, ge=0)
    enum: Optional[conlist(Any, min_items=1, unique_items=True)] = Field(None)  # type: ignore  # noqa
    type: Union[JsonType, JsonTypeArray] = Field(None)  # type: ignore
    format: Optional[str] = Field(None)

    # these will be redefined in subclasses with specific subschema types
    # just here for type-checking in the methods of this base class
    if TYPE_CHECKING:
        items: Any
        properties: Any
        all_of: Any
        any_of: Any
        one_of: Any

    @property
    def has_constraint(self) -> bool:
        return bool(_CONSTRAINT_FIELDS & self.__fields_set__)

    @property
    def has_default(self) -> bool:
        return "default" in self.__fields_set__

    @property
    def python_type(self) -> Union[Type, List[Type]]:
        if isinstance(self.type, list):
            return [_python_equivalent[t] for t in self.type]
        else:
            return _python_equivalent[self.type]

    @property
    def is_array(self) -> bool:
        return self.items is not None or self.type == "array"

    @property
    def is_object(self) -> bool:
        return (
            self.properties is not None
            or self.type == "object"
            and not self.all_of
            and not self.one_of
            and not self.any_of
            and not getattr(self, "ref", False)  # draft 6+
        )

    @root_validator(pre=True)
    def _validate_root(cls, values: Dict[str, Any]) -> Any:
        if "type" not in values and "properties" in values:
            values["type"] = "object"
        return values


class Draft04JsonSchema(_JsonSchemaBase):
    """Model for Draft 4 JSON Schema."""

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
    ref: Optional[str] = Field(None, alias="$ref")
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

    # common to all schemas (could go in _JsonSchemaBase)
    # except we need the self-referrential type to be this class
    # and... technically, all subschemas may also be booleans as of Draft 6,
    # not just additional_properties and additional_items
    additional_items: Union[bool, Draft06JsonSchema, None] = Field(None)
    items: Union[Draft06JsonSchema, List[Draft06JsonSchema], None] = Field(None)
    additional_properties: Union[bool, Draft06JsonSchema, None] = Field(None)
    definitions: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    properties: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    pattern_properties: Optional[Dict[str, Draft06JsonSchema]] = Field(None)
    all_of: Optional[List[Draft06JsonSchema]] = Field(None)
    any_of: Optional[List[Draft06JsonSchema]] = Field(None)
    one_of: Optional[List[Draft06JsonSchema]] = Field(None)
    not_: Optional[Draft06JsonSchema] = Field(None, alias="not")


class Draft07JsonSchema(_Draft06JsonSchema):
    """Model for Draft 7 JSON Schema."""

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
    definitions: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    properties: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    pattern_properties: Optional[Dict[str, Draft07JsonSchema]] = Field(None)
    all_of: Optional[List[Draft07JsonSchema]] = Field(None)
    any_of: Optional[List[Draft07JsonSchema]] = Field(None)
    one_of: Optional[List[Draft07JsonSchema]] = Field(None)
    not_: Optional[Draft07JsonSchema] = Field(None, alias="not")
