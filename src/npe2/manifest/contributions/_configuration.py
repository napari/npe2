from pydantic import BaseModel, Field, model_validator

from ._json_schema import ConfigurationJsonSchema


class ConfigurationProperty(ConfigurationJsonSchema):
    """Configuration for a single property in the plugin settings.

    This is a subset of the JSON Schema (draft 2020-12) specification.
    https://json-schema.org/draft/2020-12/ with some additional fields
    for the settings UI.
    """

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
    is_multiline: bool = Field(
        False,
        description="By default, string settings will be rendered with a single-line "
        "editor. To render with a multi-line editor, set this value to `True`.",
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
