from typing import Any, Dict, List, Literal, Optional, Pattern, Union

from pydantic import BaseModel, Field, conlist

JsonType = Literal["array", "boolean", "integer", "null", "number", "object", "string"]
StringArrayMin1 = conlist(str, unique_items=True, min_items=1)
StringArray = conlist(str, unique_items=True)
JsonTypeArray = conlist(JsonType, min_items=True, unique_items=True)


def to_camel(string: str) -> str:
    words = string.split("_")
    return words[0] + "".join(w.capitalize() for w in words[1:])


class _JsonSchemaBase(BaseModel):

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
    additional_items: Union[bool, "Draft07JsonSchema", None] = Field(None)
    items: Union["Draft07JsonSchema", List["Draft07JsonSchema"], None] = Field(None)
    max_items: Optional[int] = Field(None, ge=0)
    min_items: Optional[int] = Field(0, ge=0)
    unique_items: bool = Field(False)
    max_properties: Optional[int] = Field(None, ge=0)
    min_properties: Optional[int] = Field(0, ge=0)
    additional_properties: Union[bool, "Draft07JsonSchema", None] = Field(None)
    definitions: Optional[Dict[str, "Draft07JsonSchema"]] = Field(None)
    properties: Optional[Dict[str, "Draft07JsonSchema"]] = Field(None)
    pattern_properties: Optional[Dict[str, "Draft07JsonSchema"]] = Field(None)
    dependencies: Optional[  # type: ignore
        Dict[str, Union["Draft07JsonSchema", StringArray]]
    ] = Field(None)
    enum: Optional[conlist(Any, min_items=1, unique_items=True)] = Field(None)  # type: ignore  # noqa
    type: Union[JsonType, JsonTypeArray] = Field(None)  # type: ignore
    format: Optional[str] = Field(None)
    all_of: Optional[List["Draft07JsonSchema"]] = Field(None)
    any_of: Optional[List["Draft07JsonSchema"]] = Field(None)
    one_of: Optional[List["Draft07JsonSchema"]] = Field(None)
    not_: Optional["Draft07JsonSchema"] = Field(None, alias="not")

    class Config:  # noqa: D106
        alias_generator = to_camel


class Draft04JsonSchema(_JsonSchemaBase):
    id: Optional[str] = Field(None)
    exclusive_maximum: Optional[bool] = Field(None)
    exclusive_minimum: Optional[bool] = Field(None)
    required: Optional[StringArrayMin1] = Field(None)  # type: ignore


# technically, all subschemas may also be booleans as of Draft 6,
# not just additional_properties and additional_items
class Draft06JsonSchema(_JsonSchemaBase):
    id: Optional[str] = Field(None, alias="$id")
    ref: Optional[str] = Field(None, alias="$ref")
    examples: Optional[List[Any]] = Field(None)
    exclusive_maximum: Optional[float] = Field(None)
    exclusive_minimum: Optional[float] = Field(None)
    contains: Optional["Draft07JsonSchema"] = Field(None)
    required: Optional[StringArray] = Field(None)  # type: ignore
    property_names: Optional["Draft07JsonSchema"] = Field(None)
    const: Any = Field(None)


class Draft07JsonSchema(Draft06JsonSchema):
    """Model for Draft 7 JSON Schema."""

    comment: Optional[str] = Field(None, alias="$comment")
    read_only: bool = Field(False)
    write_only: bool = Field(False)
    content_media_type: Optional[str] = Field(None)
    content_encoding: Optional[str] = Field(None)
    if_: Optional["Draft07JsonSchema"] = Field(None, alias="if")
    then: Optional["Draft07JsonSchema"] = Field(None)
    else_: Optional["Draft07JsonSchema"] = Field(None, alias="else")


Draft07JsonSchema.update_forward_refs()
