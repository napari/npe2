from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, conlist, model_validator

from ._json_schema import (
    ConfigurationJsonSchema,
    JsonType,
    JsonTypeArray,
    _coerce_type_name,
)


class ConfigurationProperty(ConfigurationJsonSchema):
    """Configuration for a single property in the plugin settings.

    This is a subset of the JSON Schema (draft 2020-12) specification.
    https://json-schema.org/understanding-json-schema/reference
    """

    type: Annotated[JsonType | JsonTypeArray, BeforeValidator(_coerce_type_name)] = (
        Field(
            description="The type of this variable. Either JSON Schema type names "
            "('boolean', 'integer', 'number', 'string') or python type names "
            "('bool', 'int', 'float', 'str') may be used, but they will be "
            "coerced to JSON Schema types. Numbers, strings, and booleans will be "
            "editable in the UI. For boolean entries, the description "
            "will be used as the label for the checkbox.",
        )
    )

    default: Any = Field(None, description="The default value for this property.")

    description: str | None = Field(
        None,
        description="Your `description` appears after the title and before the input "
        "field, except for booleans, where the description is used as the label for "
        "the checkbox",
    )

    enum: conlist(Any, min_length=1) | None = Field(  # type: ignore
        None,
        description="A list of valid options for this field. If you provide this field,"
        "the settings UI will render a dropdown menu.",
    )
    enum_descriptions: list[str] = Field(
        default_factory=list,
        description="If you provide a list of items under the `enum` field, you may "
        "provide `enum_descriptions` to add descriptive text for each enum.",
    )

    deprecation_message: str | None = Field(
        None,
        description="If you set deprecationMessage, the setting will get a warning "
        "underline with your specified message. It won't show up in the settings "
        "UI unless it is configured by the user.",
    )
    edit_presentation: Literal["singleline", "multiline"] = Field(
        "singleline",
        description="By default, string settings will be rendered with a single-line "
        "editor. To render with a multi-line editor, set this value to `multiline`.",
    )

    @model_validator(mode="before")
    def _validate_root(cls, values):
        values = super()._validate_root(values)

        # we don't allow $ref and/or $defs in the schema
        for ignored in {"$ref", "ref", "definition", "$def"}:
            if ignored in values:
                import warnings

                del values[ignored]
                warnings.warn(
                    f"ignoring {ignored} in configuration property. "
                    "Configuration schemas must be self-contained.",
                    stacklevel=2,
                )
        return values


class ConfigurationContribution(BaseModel):
    """A configuration contribution for a plugin.

    This enables plugins to provide a schema for their configurables.
    Configuration contributions are used to generate the settings UI.
    """

    title: str = Field(
        ...,
        description="The heading used for this configuration category. Words like "
        '"Plugin", "Configuration", and "Settings" are redundant and should not be'
        "used in your title.",
    )
    properties: dict[str, ConfigurationProperty] = Field(
        ...,
        description="Configuration properties. In the settings UI, your configuration "
        "key will be used to namespace and construct a title. Though a plugin can "
        "contain multiple categories of settings, each plugin setting must still have "
        "its own unique key. Capital letters in your key are used to indicate word "
        "breaks. For example, if your key is 'gitMagic.blame.dateFormat', the "
        "generated title for the setting will look like 'Blame: Date Format'",
    )
    # order: int  # vscode uses this to sort multiple configurations
    # ... I think we can just use the order in which they are declared
