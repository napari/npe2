import pytest
from pydantic import ValidationError as PydanticValidationError

from npe2.manifest.contributions import (
    ConfigurationContribution,
    ConfigurationProperty,
    ContributionPoints,
)
from npe2.manifest.contributions._json_schema import ValidationError

PROPS = [
    {
        "heatmap_location": {
            "title": "Heatmap location",
            "type": "string",
            "default": "right",
            "enum": ["left", "right"],
            # TODO: re-enable this when we re-enable enum_descriptions
            # in ConfigurationProperty
            # "enumDescriptions": [
            #     "Adds a heatmap indicator on the left edge",
            #     "Adds a heatmap indicator on the right edge",
            # ],
        }
    }
]


@pytest.mark.parametrize("props", PROPS)
def test_config_contribution(props):
    cc = ConfigurationContribution(
        title="My Plugin",
        properties=props,
    )
    assert cc.title == "My Plugin"
    for key, val in cc.properties.items():
        assert val.model_dump(exclude_unset=True, by_alias=True) == props[key]


def test_warn_on_refs_defs():
    with pytest.warns(UserWarning):
        ConfigurationProperty(
            title="Test Property",
            type="string",
            default="baz",
            description="quux",
            ref="http://example.com",
        )


CASES = [
    ({"title": "T", "type": "string", "default": "AB", "minLength": 2}, "AB", "A"),
    ({"title": "T", "type": "string", "default": "AB", "maxLength": 3}, "AB", "ABCD"),
    ({"title": "T", "type": "integer", "default": 42}, 42, 3.123),
    ({"title": "T", "type": float, "default": 42.45}, 42.45, "3.123"),
    ({"title": "T", "type": int, "default": 30, "multipleOf": 10}, 30, 23),
    ({"title": "T", "type": "number", "default": 100, "minimum": 100}, 100, 99),
    (
        {"title": "T", "type": "number", "default": 99, "exclusiveMaximum": 100},
        99,
        100,
    ),
]


@pytest.mark.parametrize("schema, valid, invalid", CASES)
def test_config_validation(schema, valid, invalid):
    cfg = ConfigurationProperty(**schema)
    assert cfg.validate_instance(valid) == valid

    with pytest.raises(ValidationError):
        cfg.validate_instance(invalid)

    assert isinstance(cfg.has_constraint, bool)

    # check that we can convert json type to python type
    assert cfg.python_type.__module__ == "builtins"
    assert cfg.has_default is ("default" in schema)


def test_configuration_dict_keyed():
    """`contributions.configurations` is a dict keyed by configuration key."""
    cp = ContributionPoints(
        configurations={
            "reader": {
                "title": "Reader",
                "properties": {
                    "num_layers": {
                        "title": "Number of layers",
                        "type": "int",
                        "default": 3,
                    },
                },
            },
            "writer": {
                "title": "Writer",
                "properties": {
                    "compression": {
                        "title": "Compression level",
                        "type": "str",
                        "default": "medium",
                    },
                },
            },
        }
    )
    assert set(cp.configurations) == {"reader", "writer"}
    assert cp.configurations["reader"].properties["num_layers"].default == 3


@pytest.mark.parametrize(
    "key",
    [
        "my.reader",  # dots are not valid identifier characters
        "my-reader",  # dashes are not valid identifier characters
        "class",  # reserved keyword
        "1reader",  # can't start with a digit
        "_reader",  # leading underscore collides with pydantic private attrs
        "",  # empty string
    ],
)
def test_invalid_configuration_key_raises(key):
    with pytest.raises(PydanticValidationError, match="not a valid configuration key"):
        ContributionPoints(
            configurations={
                key: {
                    "title": "Reader",
                    "properties": {
                        "num_layers": {
                            "title": "Number of layers",
                            "type": "int",
                            "default": 3,
                        },
                    },
                },
            }
        )


@pytest.mark.parametrize(
    "key",
    [
        "my.lazy",
        "my-lazy",
        "class",
        "1lazy",
        "_lazy",
        "",
    ],
)
def test_invalid_property_key_raises(key):
    with pytest.raises(PydanticValidationError, match="not a valid configuration key"):
        ConfigurationContribution(
            title="My Widget",
            properties={
                key: {
                    "title": "Lazy",
                    "type": "boolean",
                    "default": False,
                },
            },
        )


def test_duplicate_configuration_titles_allowed():
    """Titles are display text only; they no longer need to be unique."""
    cp = ContributionPoints(
        configurations={
            "reader": {
                "title": "Main Widget",
                "properties": {
                    "a": {"title": "A", "type": "boolean", "default": False},
                },
            },
            "writer": {
                "title": "Main Widget",
                "properties": {
                    "b": {"title": "B", "type": "boolean", "default": False},
                },
            },
        }
    )
    assert cp.configurations["reader"].title == cp.configurations["writer"].title
