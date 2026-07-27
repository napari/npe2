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
        assert val.model_dump(exclude_unset=True, by_alias=True) == props[key]


def test_warn_on_refs_defs():
    with pytest.warns(UserWarning):
        ConfigurationProperty(
            type="string",
            default="baz",
            description="quux",
            ref="http://example.com",
        )


CASES = [
    ({"type": "string", "minLength": 2}, "AB", "A"),
    ({"type": "string", "maxLength": 3}, "AB", "ABCD"),
    ({"type": "integer"}, 42, 3.123),
    ({"type": float}, 42.45, "3.123"),
    ({"type": int, "multipleOf": 10}, 30, 23),
    ({"type": "number", "minimum": 100}, 100, 99),
    ({"type": "number", "exclusiveMaximum": 100}, 99, 100),
    ({"type": [bool, int]}, True, "True"),
]


@pytest.mark.parametrize("schema, valid, invalid", CASES)
def test_config_validation(schema, valid, invalid):
    cfg = ConfigurationProperty(**schema)
    assert cfg.validate_instance(valid) == valid

    with pytest.raises(ValidationError):
        cfg.validate_instance(invalid)

    assert isinstance(cfg.has_constraint, bool)

    # check that we can can convert json type to python type
    for t in (
        cfg.python_type if isinstance(cfg.python_type, list) else [cfg.python_type]
    ):
        assert t.__module__ == "builtins"
    assert cfg.has_default is ("default" in schema)
