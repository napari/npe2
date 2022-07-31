from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, conlist, root_validator, validator

from ._json_schema import Draft07JsonSchema, JsonType, JsonTypeArray

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


class ConfigurationProperty(Draft07JsonSchema):
    """Configuration for a single property in the plugin settings.

    This is a super-set of the JSON Schema (draft 7) specification.
    https://json-schema.org/understanding-json-schema/reference/index.html
    """

    type: Union[JsonType, JsonTypeArray] = Field(
        None,
        description="The type of this variable. Either JSON Schema type names ('array',"
        " 'boolean', 'object', ...) or python type names ('list', 'bool', 'dict', ...) "
        "may be used, but they will be coerced to JSON Schema types. Numbers, strings, "
        "and booleans will be editable in the UI, other types (lists, dicts) *may* be "
        "editable in the UI depending on their content, but maby will only be editable "
        "as text in the napari settings file. For boolean entries, the description "
        "(or markdownDescription) will be used as the label for the checkbox.",
    )
    default: Any = Field(None, description="The default value for this property.")

    description: Optional[str] = Field(
        None,
        description="Your `description` appears after the title and before the input "
        "field, except for booleans, where the description is used as the label for "
        "the checkbox. See also `markdown_description`.",
    )
    markdown_description: Optional[str] = Field(
        None,
        description="If you use `markdown_description` instead of `description`, your "
        "setting description will be rendered as Markdown in the settings UI.",
    )

    enum: Optional[conlist(Any, min_items=1, unique_items=True)] = Field(  # type: ignore # noqa: E501
        None,
        description="A list of valid options for this field. If you provide this field,"
        "the settings UI will render a dropdown menu.",
    )
    enum_descriptions: List[str] = Field(
        default_factory=list,
        description="If you provide a list of items under the `enum` field, you may "
        "provide `enum_descriptions` to add descriptive text for each enum.",
    )
    markdown_enum_descriptions: List[str] = Field(
        default_factory=list,
        description="If you use `markdown_enum_descriptions` instead of "
        "`enum_descriptions`, your descriptions will be rendered as Markdown",
    )
    # NOTE:
    # If you set both of these deprecation properties, deprecation_message will be
    # shown in the hover and the problems view, and markdown_deprecation_message will
    # be rendered as markdown in the settings UI.
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

    # scope: Literal["window", "machine"] = Field() # TODO: implement this
    edit_presentation: Literal["singleline", "multiline"] = Field(
        "singleline",
        description="A string setting can be rendered with a multiline text input if "
        'it sets "edit_presentation": "multiline"',
    )
    order: Optional[int] = Field(
        None,
        description="When specified, gives the order of this setting relative to other "
        "settings within the same category. Settings with an order property will be "
        "placed before settings without this property set; and settings without `order`"
        " will be placed in alphabetical order.",
    )

    pattern_error_message: Optional[str] = Field(
        None,
        description="When restricting string types to a given regular expression with "
        "the `pattern` field, this field may be used to provide a custom error when "
        "the pattern does not match.",
    )

    @validator("type", pre=True)
    def _coerce_type_name(cls, v):
        v = str(v).lower()
        return PY_NAME_TO_JSON_NAME.get(v, v)

    @root_validator
    def _validate_root(cls, values):
        values = super()._validate_root(values)
        for ignored in {"$ref", "ref", "definition"}:
            if ignored in values:
                import warnings

                del values[ignored]
                warnings.warn(
                    f"ignoring {ignored} in configuration property. "
                    "Configuration schemas must be self-contained."
                )


class ConfigurationContribution(BaseModel):
    title: str = Field(
        ...,
        description="The heading used for this configuration category. Words like "
        '"Plugin", "Configuration", and "Settings" are redundant and should not be'
        "used in your title.",
    )
    properties: Dict[str, ConfigurationProperty] = Field(
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
