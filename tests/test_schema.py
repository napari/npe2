from pathlib import Path

from npe2 import PluginManifest

ROOT = Path(__file__).parent.parent


def test_schema_current():
    schema_string = PluginManifest.schema_json(indent=2) + "\n"
    file = ROOT / "schema.json"
    mismatch = bool(file.exists() and file.read_text() != schema_string)
    file.write_text(schema_string)
    if mismatch:
        raise AssertionError(
            "PluginManifest schema did not match 'schema.json' in repo root.\n"
            "File has been overwritten, you can check in the result and re-test."
        )
