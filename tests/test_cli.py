import sys

import pytest

from npe2.cli import main, parse, validate


def test_cli_validate(sample_path, capsys):
    validate(sample_path / "my_plugin" / "napari.yaml")
    captured = capsys.readouterr()
    assert "✔ Manifest for 'My Plugin' valid!" in captured.out


def test_cli_validate_invalid(tmp_path, capsys):
    (tmp_path / "manifest.yaml").write_text("name: hi??\n")
    validate(tmp_path / "manifest.yaml")
    captured = capsys.readouterr()
    assert "'hi??' is not a valid python package name." in captured.out


def test_cli_validate_load_err(tmp_path, capsys):
    validate(tmp_path / "manifest.yaml")
    captured = capsys.readouterr()
    assert "🅇 Failed to load" in captured.out

    with pytest.raises(ValueError) as e:
        validate(str(tmp_path / "manifest.yaml"), debug=True)
    assert "Could not find manifest" in str(e.value)


def test_cli_parse(sample_path):
    parse(str(sample_path / "my_plugin" / "napari.yaml"))


# def test_cli_convert(sample_path, npe1_plugin_module):
#     convert(str(sample_path / "my_plugin" / "napari.yaml"))


def test_cli_main(monkeypatch, sample_path):
    cmd = ["npe2", "validate", str(sample_path / "my_plugin" / "napari.yaml")]
    monkeypatch.setattr(sys, "argv", cmd)
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0
