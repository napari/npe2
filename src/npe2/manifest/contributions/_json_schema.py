from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    AliasGenerator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    conlist,
    model_validator,
)

if TYPE_CHECKING:
    from jsonschema.exceptions import ValidationError
    from jsonschema.protocols import Validator


# use PEP562 to defer the import of jsonschema.exceptions
def __getattr__(name: str) -> Any:
    if name == "ValidationError":
        try:
            from jsonschema.exceptions import ValidationError as validation_error
        except ImportError:
            validation_error = Exception
        return validation_error
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ConfigurationJsonSchema",
    "ValidationError",
]

JsonType = Literal["boolean", "integer", "number", "string"]

PY_NAME_TO_JSON_NAME = {
    "bool": "boolean",
    "int": "integer",
    "float": "number",
    "str": "string",
}


def _to_json_type(type_: str | type) -> JsonType:
    if isinstance(type_, type):
        type_ = type_.__name__
    type_ = str(type_).lower()
    return PY_NAME_TO_JSON_NAME.get(type_, type_)  # type: ignore # (validated later)


def _to_camel(string: str) -> str:
    words = string.split("_")
    return words[0] + "".join(w.capitalize() for w in words[1:])


def _to_camel_validation(string: str) -> AliasChoices:
    camel = _to_camel(string)
    return AliasChoices(string, camel)


TO_CAMEL = AliasGenerator(alias=_to_camel, validation_alias=_to_camel_validation)


_CONSTRAINT_FIELDS = {
    "exclusive_minimum",
    "minimum",
    "exclusive_maximum",
    "maximum",
    "multiple_of",
    "min_length",
    "max_length",
}

_python_equivalent: dict[str, type] = {
    "boolean": bool,
    "integer": int,
    "number": float,
    "string": str,
}


class ConfigurationJsonSchema(BaseModel):
    """Model for (a subset of) Draft 2020-12 JSON Schema.

    This is the schema model used for the `configuration` contribution.
    https://json-schema.org/understanding-json-schema/reference
    """

    model_config = ConfigDict(alias_generator=TO_CAMEL, validate_by_name=True)

    # underscore here to avoid name collision with pydantic's `schema` method
    schema_: str = Field(
        "https://json-schema.org/draft/2020-12/schema", alias="$schema"
    )
    title: str | None = Field(None)
    description: str | None = Field(None)
    default: Any = Field(None)
    type: Annotated[JsonType, BeforeValidator(_to_json_type)] = Field()
    # constraints to specific choices
    enum: conlist(Any, min_length=1) | None = Field(None)  # type: ignore

    # min/max value for a property with type float or int
    minimum: float | int | None = Field(None)
    maximum: float | int | None = Field(None)

    # allows you to define an open interval
    exclusive_maximum: float | int | None = Field(None)
    exclusive_minimum: float | int | None = Field(None)
    # allows you to constrain number to be a multiple
    multiple_of: float | int | None = Field(None, ge=0)

    # min/max length for a property with type string
    max_length: int | None = Field(None, ge=0)
    min_length: int | None = Field(0, ge=0)

    _json_validator: builtins.type[Validator] = PrivateAttr()

    @model_validator(mode="before")
    def _validate_root(cls, values: dict[str, Any]) -> Any:
        # TODO: is this still true?
        # Get around pydantic bug wherein `Optional[conlists]`` throw a
        # 'NoneType' object is not iterable error if `None` is provided in init.
        if "enum" in values and not values["enum"]:
            values.pop("enum")

        return values

    @property
    def has_constraint(self) -> bool:
        """Return True if this schema has any constraints."""
        return bool(_CONSTRAINT_FIELDS & self.model_fields_set)

    @property
    def has_default(self) -> bool:
        """Return True if the schema has a default value."""
        return "default" in self.model_fields_set

    @property
    def python_type(self) -> builtins.type:
        """Return the Python type equivalent for this schema's (JSON) type."""
        return _python_equivalent[self.type]

    @property
    def json_validator(self) -> builtins.type[Validator]:
        """Return jsonschema validator class for this schema.

        See also `validate_instance`.
        """
        if not hasattr(self, "_json_validator"):
            from jsonschema.validators import validator_for

            schema = self.model_dump(by_alias=True, exclude_unset=True)
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
