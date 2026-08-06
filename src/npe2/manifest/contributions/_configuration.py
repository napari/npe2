import re
from collections.abc import Iterable

from pydantic import BaseModel, Field, model_validator

from ._json_schema import ConfigurationJsonSchema


def normalize_title(title: str) -> str:
    """Return a canonical snake_case key for a configuration title.

    Configuration titles are free-form text (e.g. "Demo Configuration for
    widget 1") but consumers (e.g. napari) use them to derive identifier-like
    keys / field names.  Normalizing titles to a canonical key lets npe2
    enforce that titles are unique within a plugin, and lets consumers reuse
    the same normalization instead of implementing (possibly divergent) ones.

    Examples
    --------
    >>> normalize_title('Demo Configuration for widget 1')
    'demo_configuration_for_widget_1'
    >>> normalize_title('main widget')
    'main_widget'
    """
    # camelCase -> snake_case (e.g. someSetting -> some_Setting)
    name = re.sub(r"(?<!^)(?=[A-Z])", "_", title)
    # any run of non-alphanumeric characters is a separator
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_").lower()
    if not name:
        name = "settings"
    if name[0].isdigit():
        name = f"_{name}"
    return name


def _ensure_unique_normalized(items: Iterable[str], what: str) -> None:
    """Raise if any two strings in ``items`` normalize to the same key.

    Parameters
    ----------
    items : Iterable[str]
        The free-form strings to check for collisions after
        :func:`normalize_title`.
    what : str
        Human-readable noun phrase used in the error message, e.g.
        "Configuration titles".
    """
    seen: dict[str, str] = {}
    for original in items:
        key = normalize_title(original)
        if key in seen:
            raise ValueError(
                f"{what} {seen[key]!r} and {original!r} both normalize to "
                f"{key!r}; duplicate {what.lower()} are not allowed (case, "
                "whitespace, and punctuation are ignored)."
            )
        seen[key] = original


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
        description="Configuration properties. The key is used to namespace each "
        "setting and to derive its internal identifier (e.g. field name); the "
        "`title` of each property is what the settings UI displays as its label. "
        "Though a plugin can contain multiple categories of settings, each plugin "
        "setting must still have its own unique key.",
    )

    @model_validator(mode="after")
    def _validate_unique_property_keys(self):
        """Property keys must be unique once normalized to snake_case."""
        _ensure_unique_normalized(self.properties, "Configuration properties")
        return self

    # order: int  # vscode uses this to sort multiple configurations
    # ... I think we can just use the order in which they are declared
