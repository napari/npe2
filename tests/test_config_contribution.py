import pytest

from npe2.manifest.contributions import ConfigurationContribution, ConfigurationProperty
from npe2.manifest.contributions._json_schema import ValidationError

PROPS = [
    {
        "plugin.heatmap.location": {
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
        assert val.dict(exclude_unset=True, by_alias=True) == props[key]


def test_warn_on_refs_defs():
    with pytest.warns(UserWarning):
        ConfigurationProperty(
            type="string",
            default="baz",
            description="quux",
            ref="http://example.com",
        )


CASES = [
    (
        {
            "type": str,
            "pattern": "^(\\([0-9]{3}\\))?[0-9]{3}-[0-9]{4}$",
            "pattern_error_message": "custom error",
        },
        "555-1212",
        "(888)555-1212 ext. 532",
    ),
    ({"type": "string", "minLength": 2}, "AB", "A"),
    ({"type": "string", "maxLength": 3}, "AB", "ABCD"),
    ({"type": "integer"}, 42, 3.123),
    ({"type": float}, 42.45, "3.123"),
    ({"type": int, "multipleOf": 10}, 30, 23),
    ({"type": "number", "minimum": 100}, 100, 99),
    ({"type": "number", "exclusiveMaximum": 100}, 99, 100),
    (
        {"properties": {"number": {"type": "number"}}},
        {"number": 1600},
        {"number": "1600"},
    ),
    (
        {
            "type": dict,
            "properties": {
                "number": {"type": "number"},
            },
            "additional_properties": False,
        },
        {"number": 1600},
        {"number": 1600, "street_name": "Pennsylvania"},
    ),
    ({"type": "array"}, [3, "diff", {"types": "of values"}], {"Not": "an array"}),
    ({"items": {"type": "number"}}, [1, 2, 3, 4, 5], [1, 2, "3", 4, 5]),
    (
        {
            "items": [
                {"type": "number"},
                {"type": "string"},
                {"enum": ["Street", "Avenue", "Boulevard"]},
                {"enum": ["NW", "NE", "SW", "SE"]},
            ]
        },
        [1600, "Pennsylvania", "Avenue", "NW"],
        [24, "Sussex", "Drive"],
    ),
    ({"type": [bool, int]}, True, "True"),
]


@pytest.mark.parametrize("schema, valid, invalid", CASES)
def test_config_validation(schema, valid, invalid):
    cfg = ConfigurationProperty(**schema)
    assert cfg.validate_instance(valid) == valid

    match = schema.get("pattern_error_message", None)
    with pytest.raises(ValidationError, match=match):
        assert cfg.validate_instance(invalid)

    assert cfg.is_array is ("items" in schema or cfg.type == "array")
    assert cfg.is_object is (cfg.type == "object")
    assert isinstance(cfg.has_constraint, bool)

    # check that we can can convert json type to python type
    for t in (
        cfg.python_type if isinstance(cfg.python_type, list) else [cfg.python_type]
    ):
        assert t.__module__ == "builtins"
    assert cfg.has_default is ("default" in schema)
