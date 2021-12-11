"""
JsonSchemaObject class below vendored/modified from datamodel-code-generator

MIT License

Copyright (c) 2019 Koudai Aono

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Extra, Field, root_validator, validator
from typing_extensions import Literal

JsonType = Union[
    Literal["string"],
    Literal["number"],
    Literal["integer"],
    Literal["object"],
    Literal["array"],
    Literal["boolean"],
    Literal["null"],
]

_python_equivalent: Dict[Optional[str], Type] = {
    "string": str,
    "number": float,
    "integer": int,
    "object": dict,
    "array": list,
    "boolean": bool,
    "null": type(None),
    None: object,
}


class JSONReference(Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"
    URL = "URL"


_CONSTRAINED_FIELDS = {
    "exclusiveMinimum",
    "minimum",
    "exclusiveMaximum",
    "maximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "pattern",
}


class JsonSchemaObject(BaseModel):
    items: Union[List["JsonSchemaObject"], "JsonSchemaObject", None]
    uniqueItem: Optional[bool]
    type: Union[JsonType, List[JsonType], None]
    format: Optional[str]
    pattern: Optional[str]
    minLength: Optional[int]
    maxLength: Optional[int]
    minimum: Optional[float]
    maximum: Optional[float]
    minItems: Optional[int]
    maxItems: Optional[int]
    multipleOf: Optional[float]
    exclusiveMaximum: Union[float, bool, None]
    exclusiveMinimum: Union[float, bool, None]
    additionalProperties: Union["JsonSchemaObject", bool, None]
    oneOf: List["JsonSchemaObject"] = []
    anyOf: List["JsonSchemaObject"] = []
    allOf: List["JsonSchemaObject"] = []
    enum: List[Any] = []
    enum_descriptions: List[str] = Field(
        default_factory=list, description="provides descriptive text for each enum."
    )
    markdown_enum_descriptions: Optional[List[str]] = Field(
        default_factory=list,
        description="If you use markdown_enum_descriptions instead of "
        "enum_descriptions, your descriptions will be rendered as Markdown",
    )
    writeOnly: Optional[bool]
    properties: Optional[Dict[str, "JsonSchemaObject"]]
    required: List[str] = []
    nullable: Optional[bool] = False
    x_enum_varnames: List[str] = Field(default_factory=list)
    description: Optional[str]
    markdown_description: Optional[str] = Field(
        None,
        description="If you use markdown_description instead of description, your "
        "setting description will be rendered as Markdown in the settings UI.",
    )

    deprecation_message: Optional[str] = Field(
        None,
        description="If you set deprecationMessage, the setting will get a warning "
        "underline with your specified message. It won't show up in the settings "
        "UI unless it is configured by the user.",
    )
    markdown_deprecation_message: Optional[str] = Field(
        None,
        description="If you set markdown_deprecation_message, the setting will get a "
        "warning underline with your specified message. It won't show up in the "
        "settings UI unless it is configured by the user.",
    )
    # NOTE:
    # If you set both properties, deprecation_message will be shown in the hover and
    # the problems view, and markdown_deprecation_message will be rendered as markdown
    # in the settings UI.
    title: Optional[str]
    example: Any
    examples: Any
    default: Any
    id: Optional[str] = Field(default=None)
    custom_type_path: Optional[str] = Field(default=None)
    _raw: Dict[str, Any]

    @root_validator(pre=True)
    def validate_exclusive_maximum_and_exclusive_minimum(
        cls, values: Dict[str, Any]
    ) -> Any:
        if "$ref" in values:
            # ref not supported
            values.pop("$ref")

        exclusive_maximum: Union[float, bool, None] = values.get("exclusiveMaximum")
        exclusive_minimum: Union[float, bool, None] = values.get("exclusiveMinimum")

        if exclusive_maximum is True:
            values["exclusiveMaximum"] = values["maximum"]
            del values["maximum"]
        elif exclusive_maximum is False:
            del values["exclusiveMaximum"]
        if exclusive_minimum is True:
            values["exclusiveMinimum"] = values["minimum"]
            del values["minimum"]
        elif exclusive_minimum is False:
            del values["exclusiveMinimum"]

        if "type" not in values and "properties" in values:
            values["type"] = "object"
        return values

    class Config:
        extra = Extra.forbid
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._raw = data

    @property
    def extras(self) -> Dict[str, Any]:
        return {k: v for k, v in self._raw.items() if k not in EXCLUDE_FIELD_KEYS}

    @property
    def is_object(self) -> bool:
        return (
            self.properties is not None
            or self.type == "object"
            and not self.allOf
            and not self.oneOf
            and not self.anyOf
            and not getattr(self, "ref", False)
        )

    @property
    def python_type(self) -> Union[Type, List[Type]]:
        if isinstance(self.type, list):
            return [_python_equivalent[t] for t in self.type]
        else:
            return _python_equivalent[self.type]

    @property
    def is_array(self) -> bool:
        return self.items is not None or self.type == "array"

    @validator("items", pre=True)
    def validate_items(cls, values: Any) -> Any:
        # this condition expects empty dict
        return values or None

    @property
    def has_default(self) -> bool:
        return "default" in self.__fields_set__

    @property
    def has_constraint(self) -> bool:
        return bool(_CONSTRAINED_FIELDS & self.__fields_set__)

    # refs not supported
    # ref: Optional[str] = Field(default=None, alias="$ref")

    # @validator("ref")
    # def validate_ref(cls, value: Any) -> Any:
    #     if isinstance(value, str) and "#" in value:
    #         if value.endswith("#/"):
    #             return value[:-1]
    #         elif "#/" in value or value[0] == "#" or value[-1] == "#":
    #             return value
    #         return value.replace("#", "#/")
    #     return value

    # @property
    # def ref_object_name(self) -> Optional[str]:
    #     return self.ref.rsplit("/", 1)[-1] if self.ref else None

    # @property
    # def ref_type(self) -> Optional[JSONReference]:
    #     if self.ref:
    #         return get_ref_type(self.ref)
    #     return None


# def is_url(ref: str) -> bool:
#     return ref.startswith(("https://", "http://"))


# @lru_cache()
# def get_ref_type(ref: str) -> JSONReference:
#     if ref[0] == "#":
#         return JSONReference.LOCAL
#     elif is_url(ref):
#         return JSONReference.URL
#     return JSONReference.REMOTE


JsonSchemaObject.update_forward_refs()

DEFAULT_FIELD_KEYS: Set[str] = {
    "example",
    "examples",
    "description",
    "title",
}

EXCLUDE_FIELD_KEYS = (set(JsonSchemaObject.__fields__) - DEFAULT_FIELD_KEYS) | {
    "$id",
    "$ref",
}
