import warnings
from enum import Enum
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
        msg = f"✔ Manifest for {pm.display_name!r} valid!"
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


class ManifestFormat(str, Enum):
    yaml = "yaml"
    json = "json"
    toml = "toml"


@app.command()
def convert(
    plugin_name: str = typer.Argument(..., help="The name of the plugin to convert"),
    format: ManifestFormat = ManifestFormat.yaml,
    out: Optional[Path] = None,
):
    """Convert existing plugin to new manifest."""
    from ._from_npe1 import manifest_from_npe1

    try:
        with warnings.catch_warnings(record=True) as w:
            pm = manifest_from_npe1(plugin_name)
        if w:
            typer.secho("Some errors occured:", fg=typer.colors.RED, bold=False)
            for r in w:
                typer.secho(
                    indent(str(r.message), "  "),
                    fg=typer.colors.MAGENTA,
                    bold=False,
                )
            print()

        mf = getattr(pm, format)()
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit()

    if out is not None:
        with open(out, "w") as fh:
            fh.write(mf)
    else:
        print(mf)


def main():
    app()
