import warnings
from pathlib import Path
from textwrap import indent
from typing import Optional

import typer

from npe2 import PluginManifest

app = typer.Typer()


def _pprint_yaml(string):
    """Print yaml nicely, depending on available modules."""
    try:
        from rich.console import Console
        from rich.syntax import Syntax

        Console().print(Syntax(string, "yaml", theme="fruity"))
    except Exception:
        typer.echo(string)


@app.command()
def validate(name: str, debug: bool = False):
    """Validate manifest for a distribution name or manifest filepath."""

    valid = False
    try:
        pm = PluginManifest._from_package_or_name(name)
        msg = f"✔ Manifest for {(pm.display_name or pm.name)!r} valid!"
        valid = True
    except PluginManifest.ValidationError as err:
        msg = f"🅇 Invalid! {err}"
    except Exception as err:
        msg = f"🅇 Failed to load {name!r}. {type(err).__name__}: {err}"
        if debug:
            raise

    typer.secho(msg, fg=typer.colors.GREEN if valid else typer.colors.RED, bold=True)


@app.command()
def parse(name: str):
    """Show parsed manifest as yaml"""
    pm = PluginManifest._from_package_or_name(name)
    _pprint_yaml(pm.yaml())


@app.command()
def convert(
    path: Path = typer.Argument(
        ...,
        help="Path of a local repository to convert (package must also be installed in"
        " current environment). Or, the name of an installed package/plugin. If a "
        "package is provided instead of a directory, the new manifest will simply be "
        "printed to stdout.",
    ),
    dry_run: Optional[bool] = typer.Option(
        False,
        "--dry-runs",
        "-n",
        help="Just print manifest to stdout. Do not modify anything",
    ),
):
    """Convert first generation napari plugin to new (manifest) format."""
    from ._from_npe1 import convert_repository, manifest_from_npe1

    try:
        with warnings.catch_warnings(record=True) as w:
            if path.is_dir():
                pm, mf_path = convert_repository(path, dry_run=dry_run)
            else:
                pm = manifest_from_npe1(str(path))
        if w:
            typer.secho("Some issues occured:", fg=typer.colors.RED, bold=False)
            for r in w:
                typer.secho(
                    indent(str(r.message), "  "),
                    fg=typer.colors.MAGENTA,
                    bold=False,
                )
            print()
    except Exception as e:
        msg = f"Conversion failed:\n{type(e).__name__}: {e}"
        typer.secho(msg, fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)

    if dry_run or not path.is_dir():
        if path.is_dir():
            typer.secho(
                f"# Manifest would be written to {mf_path}",
                fg=typer.colors.BRIGHT_GREEN,
                bold=False,
            )
        _pprint_yaml(pm.yaml())
    else:
        msg = f"✔  Conversion complete! New manifest at {mf_path}."
        typer.secho(msg, fg=typer.colors.GREEN, bold=True)
        typer.secho(
            "If you have any napari_plugin_engine imports or hook_implementation "
            "decorators, you may remove them now.",
            fg=typer.colors.GREEN,
            bold=False,
        )


def main():
    app()
