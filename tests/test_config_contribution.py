import pytest
from pydantic import ValidationError as PydanticValidationError

from npe2.manifest.contributions import (
    ConfigurationContribution,
    ConfigurationProperty,
    ContributionPoints,
)
from npe2.manifest.contributions._configuration import normalize_title
from npe2.manifest.contributions._json_schema import ValidationError

PROPS = [
    {
        "plugin.heatmap.location": {
            "title": "Heatmap location",
            "type": "string",
            "default": "right",
            "enum": ["left", "right"],
            "enumDescriptions": [
                "Adds a heatmap indicator on the left edge",
                "Adds a heatmap indicator on the right edge",
            ],
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


def test_normalize_title():
    assert (
        normalize_title("Demo Configuration for widget 1")
        == "demo_configuration_for_widget_1"
    )
    assert normalize_title("main widget") == "main_widget"
    assert normalize_title("someSetting") == "some_setting"


def test_duplicate_configuration_titles_raise():
    with pytest.raises(PydanticValidationError, match="both normalize to"):
        ContributionPoints(
            configuration=[
                {
                    "title": "Main Widget",
                    "properties": {
                        "p.a": {
                            "title": "A",
                            "type": "boolean",
                            "default": False,
                        },
                    },
                },
                {
                    "title": "main widget",
                    "properties": {
                        "p.b": {
                            "title": "B",
                            "type": "boolean",
                            "default": False,
                        },
                    },
                },
            ]
        )


def test_duplicate_property_keys_raise():
    with pytest.raises(PydanticValidationError, match="both normalize to"):
        ConfigurationContribution(
            title="My Widget",
            properties={
                "plugin.a.lazy": {
                    "title": "Lazy",
                    "type": "boolean",
                    "default": False,
                },
                "plugin.a-lazy": {
                    "title": "Lazy 2",
                    "type": "boolean",
                    "default": False,
                },
            },
        )
