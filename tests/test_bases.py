import json

import pytest
import yaml

from npe2 import PluginManifest

MINIMAL_MANIFEST = {
    "name": "my-plugin",
    "contributions": {
        "commands": [
            {
                "id": "my-plugin.hello",
                "title": "Hello",
                "python_name": "my_plugin:hello",
            },
        ],
        "menus": {
            "napari/layers/context": [
                {"command": "my-plugin.hello"},
            ],
        },
    },
}


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_yaml_duplicate_top_level_menu_key_raises(tmp_path):
    text = """
name: my-plugin
contributions:
  commands:
    - id: my-plugin.hello
      title: Hello
      python_name: my_plugin:hello
  menus:
    napari/layers/context:
      - command: my-plugin.hello
    napari/layers/context:
      - command: my-plugin.hello
"""
    path = _write(tmp_path, "napari.yaml", text)
    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        PluginManifest.from_file(path)


def test_json_duplicate_top_level_menu_key_raises(tmp_path):
    # can't use json.dumps for this -- it would collapse the duplicate key
    # before we ever get to write the file.
    text = """
{
  "name": "my-plugin",
  "contributions": {
    "commands": [
      {"id": "my-plugin.hello", "title": "Hello", "python_name": "my_plugin:hello"}
    ],
    "menus": {
      "napari/layers/context": [{"command": "my-plugin.hello"}],
      "napari/layers/context": [{"command": "my-plugin.hello"}]
    }
  }
}
"""
    path = _write(tmp_path, "napari.json", text)
    with pytest.raises(ValueError, match="Duplicate key 'napari/layers/context'"):
        PluginManifest.from_file(path)


def test_yaml_repeated_sibling_key_names_are_fine(tmp_path):
    """The same key name in unrelated, sibling mappings is not a collision."""
    text = yaml.safe_dump(MINIMAL_MANIFEST)
    path = _write(tmp_path, "napari.yaml", text)
    mf = PluginManifest.from_file(path)
    assert mf.contributions.menus["napari/layers/context"][0].command == (
        "my-plugin.hello"
    )


def test_json_repeated_sibling_key_names_are_fine(tmp_path):
    text = json.dumps(MINIMAL_MANIFEST)
    path = _write(tmp_path, "napari.json", text)
    mf = PluginManifest.from_file(path)
    assert mf.contributions.menus["napari/layers/context"][0].command == (
        "my-plugin.hello"
    )


def test_toml_duplicate_table_raises(tmp_path):
    """tomllib already rejects duplicate keys per the TOML spec; nothing npe2-specific
    is needed here, but we assert on it so a regression would be caught."""
    text = """
name = "my-plugin"

[[contributions.commands]]
id = "my-plugin.hello"
title = "Hello"
python_name = "my_plugin:hello"

[contributions.menus]
"napari/layers/context" = [{command = "my-plugin.hello"}]
"napari/layers/context" = [{command = "my-plugin.hello"}]
"""
    path = _write(tmp_path, "napari.toml", text)
    with pytest.raises(Exception, match=r"twice|Cannot overwrite"):
        PluginManifest.from_file(path)
