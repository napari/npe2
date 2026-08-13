from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

from npe2.manifest import _validators

from ._json_schema import ConfigurationJsonSchema


class ConfigurationProperty(ConfigurationJsonSchema):
    """Configuration for a single property in the plugin settings.

    This is a subset of the JSON Schema (draft 2020-12) specification.
    https://json-schema.org/draft/2020-12/ with some additional fields
    for the settings UI.
    """

    # TODO: commenting these out so we can unblock napari 0.9.0
    # will bring them back in a future PR

    # enum_descriptions: list[str] = Field(
    #     default_factory=list,
    #     description="If you provide a list of items under the `enum` field, you may "
    #     "provide `enum_descriptions` to add descriptive text for each enum.",
    # )
    # deprecation_message: str | None = Field(
    #     None,
    #     description="If you set deprecationMessage, the setting will get a warning "
    #     "underline with your specified message. It won't show up in the settings "
    #     "UI unless it is configured by the user.",
    # )
    # is_multiline: bool = Field(
    #     False,
    #     description="By default, string settings will be rendered with a single-line "
    #     "editor. To render with a multi-line editor, set this value to `True`.",
    # )

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


_ConfigurationKey = Annotated[str, AfterValidator(_validators.configuration_key)]


class ConfigurationContribution(BaseModel):
    """A configuration contribution for a plugin.

    This enables plugins to provide a schema for their configurables.
    Configuration contributions are used to generate the settings UI. Each
    configuration contribution is declared under a unique key in
    `contributions.configurations` (see `ContributionPoints.configurations`);
    that key, together with each property's key below, is used verbatim to
    build the path used to access this setting at runtime, e.g.
    `get_plugin_settings('plugin-name').<configuration-key>.<property-key>`.
    """

    title: str = Field(
        ...,
        description="The heading used for this configuration category, displayed in "
        'the settings UI. Words like "Plugin", "Configuration", and "Settings" '
        "are redundant and should not be used in your title. Unlike the key under "
        "which this contribution is declared in `contributions.configurations`, the "
        "title is display text only and does not need to be unique.",
    )
    properties: dict[_ConfigurationKey, ConfigurationProperty] = Field(
        ...,
        description="Configuration properties, keyed by a property key that is local "
        "to this configuration contribution. Each property key must be a valid, "
        "non-reserved Python identifier that does not begin with an underscore, "
        "since it is used verbatim as the attribute name for that setting on the "
        "generated settings model (e.g. "
        "`get_plugin_settings('plugin-name').<configuration-key>.<property-key>`). "
        "Property keys only need to be unique within this configuration "
        "contribution, not across the whole plugin.",
    )

    # order: int  # vscode uses this to sort multiple configurations
    # ... I think we can just use the order in which they are declared
