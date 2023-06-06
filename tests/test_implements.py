import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

import npe2.implements
from npe2 import PluginManifest
from npe2._inspection import find_npe2_module_contributions

SAMPLE_PLUGIN_NAME = "my-plugin"
SAMPLE_MODULE_NAME = "my_plugin"
SAMPLE_DIR = Path(__file__).parent / "sample"


def test_extract_manifest():
    module_with_decorators = SAMPLE_DIR / "_with_decorators.py"
    extracted = find_npe2_module_contributions(
        module_with_decorators,
        plugin_name=SAMPLE_PLUGIN_NAME,
        module_name=SAMPLE_MODULE_NAME,
    )
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
    _id = lambda x: x.id  # noqa
    assert sorted(extracted.commands, key=_id) == sorted(expected.commands, key=_id)
    k = lambda x: x.command  # noqa
    assert sorted(extracted.readers, key=k) == sorted(expected.readers, key=k)
    assert sorted(extracted.writers, key=k) == sorted(expected.writers, key=k)
    assert sorted(extracted.widgets, key=k) == sorted(expected.widgets, key=k)
    assert sorted(extracted.sample_data, key=k) == sorted(expected.sample_data, key=k)


def test_dynamic(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(sys, "path", [*sys.path, str(SAMPLE_DIR)])
        import _with_decorators

        assert hasattr(_with_decorators.get_reader, "_npe2_ReaderContribution")
        info = _with_decorators.get_reader._npe2_ReaderContribution
        assert info == {
            "id": "some_reader",
            "title": "Some Reader",
            "filename_patterns": ["*.fzy", "*.fzzy"],
            "accepts_directories": True,
        }

        # we can compile a module object as well as a string path
        extracted = find_npe2_module_contributions(
            _with_decorators,
            plugin_name=SAMPLE_PLUGIN_NAME,
            module_name=SAMPLE_MODULE_NAME,
        )

        assert extracted.commands


@pytest.mark.parametrize("check", [True, False])
def test_decorator_arg_check(check):
    """Check that the decorators don't check arguments at runtime unless instructed."""
    # tilde is wrong and filename_patterns is missing
    kwargs = {"id": "some_id", "tilde": "some_title"}
    kwargs[npe2.implements.CHECK_ARGS_PARAM] = check
    ctx = pytest.raises(TypeError) if check else nullcontext()
    with ctx:
        npe2.implements.reader(**kwargs)(lambda: None)
