import sys

import pytest
from typer.testing import CliRunner

from npe2.cli import app, main
from npe2.manifest.schema import PluginManifest

runner = CliRunner()


@pytest.mark.parametrize("debug", ["--debug", ""])
@pytest.mark.parametrize("imports", ["--imports", "--no-imports"])
def test_cli_validate_ok(sample_path, debug, imports, monkeypatch):
    cmd = ["validate", str(sample_path / "my_plugin" / "napari.yaml"), imports]
    if debug:
        cmd += [debug]
    with monkeypatch.context() as m:
        m.setattr(sys, "path", sys.path + [str(sample_path)])
        result = runner.invoke(app, cmd)
    assert "✔ Manifest for 'My Plugin' valid!" in result.stdout
    assert result.exit_code == 0


def test_cli_validate_invalid(tmp_path, capsys):
    (tmp_path / "manifest.yaml").write_text("name: hi??\n")
    cmd = ["validate", str(tmp_path / "manifest.yaml")]
    result = runner.invoke(app, cmd)
    assert "'hi??' is not a valid python package name." in result.stdout


def test_cli_validate_load_err(tmp_path):
    non_existent = str(tmp_path / "manifest.yaml")
    result = runner.invoke(app, ["validate", non_existent])
    assert result.exit_code == 1
    assert "🅇 Unexpected error in" in result.stdout
    assert "Could not find manifest for" in result.stdout

    result = runner.invoke(app, ["validate", non_existent, "--debug"])
    assert "Could not find manifest for" in result.stdout


@pytest.mark.parametrize("format", ["json", "yaml", "toml", "csv"])
@pytest.mark.parametrize("to_file", [True, False])
def test_cli_parse(sample_path, format, tmp_path, to_file):
    cmd = ["parse", str(sample_path / "my_plugin" / "napari.yaml")]
    if to_file:
        dest = tmp_path / f"output.{format}"
        cmd.extend(["-o", str(dest)])
    else:
        cmd.extend(["-f", format])

    result = runner.invoke(app, cmd)
    if format == "csv":
        assert result.exit_code
        return

    assert result.exit_code == 0
    if to_file:
        assert dest.exists()
        assert PluginManifest.from_file(dest)
    else:
        assert "my-plugin" in result.stdout  # just prints the yaml


@pytest.mark.parametrize("format", ["json", "yaml", "toml", "csv"])
@pytest.mark.parametrize("to_file", [True, False])
@pytest.mark.parametrize("include_meta", [True, False])
def test_cli_fetch(format, tmp_path, to_file, include_meta):
    cmd = ["fetch", "napari-omero"]
    if to_file:
        dest = tmp_path / f"output.{format}"
        cmd.extend(["-o", str(dest)])
    else:
        cmd.extend(["-f", format])
    if include_meta:
        cmd.extend(["--include-package-meta", "--indent=2"])

    result = runner.invoke(app, cmd)
    if format == "csv":
        assert result.exit_code
        return

    assert result.exit_code == 0
    if to_file:
        assert dest.exists()
        assert PluginManifest.from_file(dest)
    else:
        assert "napari-omero" in result.stdout  # just prints the yaml
        if include_meta:
            assert "package_metadata" in result.stdout


@pytest.mark.filterwarnings("default:Failed to convert")
def test_cli_convert_repo(npe1_repo, mock_npe1_pm_with_plugin):
    result = runner.invoke(app, ["convert", str(npe1_repo)])
    assert result.exit_code == 0
    assert "✔  Conversion complete!" in result.stdout


@pytest.mark.filterwarnings("default:Failed to convert")
def test_cli_convert_repo_dry_run(npe1_repo, mock_npe1_pm_with_plugin):
    result = runner.invoke(app, ["convert", str(npe1_repo), "-n"])
    assert result.exit_code == 0
    assert "# Manifest would be written to" in result.stdout


@pytest.mark.filterwarnings("ignore:The distutils package is deprecated")
@pytest.mark.filterwarnings("default:Failed to convert napari_get_writer")
def test_cli_convert_svg():
    result = runner.invoke(app, ["convert", "napari-svg"])
    assert "Some issues occured:" in result.stdout
    assert "Found a multi-layer writer in 'napari-svg'" in result.stdout
    assert result.exit_code == 0


def test_cli_convert_repo_fails(npe1_repo, mock_npe1_pm_with_plugin):
    (npe1_repo / "setup.cfg").unlink()
    result = runner.invoke(app, ["convert", str(npe1_repo)])
    assert result.exit_code == 1
    assert "Could not detect first gen napari plugin package" in result.stdout


@pytest.mark.filterwarnings("default:Failed to convert")
def test_cli_convert_package_name(npe1_repo, mock_npe1_pm_with_plugin):
    result = runner.invoke(app, ["convert", "npe1-plugin"])
    assert "name: npe1-plugin" in result.stdout  # just prints the yaml
    assert result.exit_code == 0


def test_cli_main(monkeypatch, sample_path):
    cmd = ["npe2", "validate", str(sample_path / "my_plugin" / "napari.yaml")]
    monkeypatch.setattr(sys, "argv", cmd)
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def test_cli_cache_list_empty(mock_cache):
    result = runner.invoke(app, ["cache", "--list"])
    assert "Nothing cached" in result.stdout
    assert result.exit_code == 0


def test_cli_cache_list_full(uses_npe1_plugin, mock_cache):
    (mock_cache / "npe1-plugin.yaml").write_text("name: npe1-plugin\n")
    result = runner.invoke(app, ["cache", "--list"])
    assert result.stdout == "npe1-plugin: 0.1.0\n"
    assert result.exit_code == 0


def test_cli_cache_list_named(uses_npe1_plugin, mock_cache):
    (mock_cache / "npe1-plugin.yaml").write_text("name: npe1-plugin\n")
    result = runner.invoke(app, ["cache", "--list", "not-a-plugin"])
    assert result.stdout == "Nothing cached for plugins: not-a-plugin\n"
    assert result.exit_code == 0


def test_cli_cache_clear_empty(mock_cache):
    result = runner.invoke(app, ["cache", "--clear"])
    assert "Nothing to clear" in result.stdout
    assert result.exit_code == 0


def test_cli_cache_clear_full(mock_cache):
    (mock_cache / "npe1-plugin.yaml").write_text("name: npe1-plugin\n")
    result = runner.invoke(app, ["cache", "--clear"])
    assert "Cleared these files from cache" in result.stdout
    assert "- npe1-plugin.yaml" in result.stdout
    assert result.exit_code == 0


def test_cli_cache_clear_named(mock_cache):
    (mock_cache / "npe1-plugin.yaml").write_text("name: npe1-plugin\n")
    result = runner.invoke(app, ["cache", "--clear", "not-a-plugin"])
    assert result.stdout == "Nothing to clear for plugins: not-a-plugin\n"
    assert result.exit_code == 0
