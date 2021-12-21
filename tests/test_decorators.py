from pathlib import Path

from npe2 import PluginManifest
from npe2.implements import compile
from npe2.manifest.contributions import ContributionPoints

SAMPLE_PLUGIN_NAME = "my-plugin"
SAMPLE_MODULE_NAME = "my_plugin"


def test_extract_manifest():
    module_with_decorators = Path(__file__).parent / "sample" / "_with_decorators.py"
    output = compile(
        module_with_decorators,
        plugin_name=SAMPLE_PLUGIN_NAME,
        module_name=SAMPLE_MODULE_NAME,
    )
    extracted = ContributionPoints(**output)
    assert extracted.commands
    assert extracted.readers
    assert extracted.writers
    assert extracted.widgets
    assert extracted.sample_data

    # get expectations from manually created manifest
    known_manifest = Path(__file__).parent / "sample" / "my_plugin" / "napari.yaml"
    expected = PluginManifest.from_file(known_manifest).contributions
    non_python = ("my-plugin.hello_world", "my-plugin.another_command")
    expected.commands = [c for c in expected.commands if c.id not in non_python]
    expected.sample_data = [c for c in expected.sample_data if not hasattr(c, "uri")]

    # check that they're all the same
    id = lambda x: x.id  # noqa
    assert sorted(extracted.commands, key=id) == sorted(expected.commands, key=id)
    k = lambda x: x.command  # noqa
    assert sorted(extracted.readers, key=k) == sorted(expected.readers, key=k)
    assert sorted(extracted.writers, key=k) == sorted(expected.writers, key=k)
    assert sorted(extracted.widgets, key=k) == sorted(expected.widgets, key=k)
    assert sorted(extracted.sample_data, key=k) == sorted(expected.sample_data, key=k)
