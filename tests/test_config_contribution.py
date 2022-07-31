import pytest

from npe2.manifest.contributions import ConfigurationContribution, ConfigurationProperty

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
