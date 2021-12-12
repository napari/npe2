import warnings
from pathlib import Path
from textwrap import indent
from typing import Optional

import typer

from npe2 import PluginManifest

app = typer.Typer()


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

    try:
        from rich.console import Console
        from rich.syntax import Syntax

        Console().print(Syntax(pm.yaml(), "yaml", theme="fruity"))
    except Exception:
        typer.echo(pm.yaml())


@app.command()
def convert(
    path: Path = typer.Argument(..., help="The path of the repository to convert."),
    just_print: Optional[bool] = typer.Option(
        False, help="Just print manifest to stdout. Do not modify anything"
    ),
):
    """Convert existing plugin to new manifest."""
    from ._from_npe1 import convert_repository

    try:
        with warnings.catch_warnings(record=True) as w:
            pm, mf_path = convert_repository(path, _just_manifest=just_print)
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

    if just_print:
        print(pm.yaml())
    else:
        msg = f"✔  Conversion complete! New manifest at {mf_path}"
        typer.secho(msg, fg=typer.colors.GREEN, bold=True)


def main():
    app()
