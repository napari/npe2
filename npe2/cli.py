from npe2 import PluginManifest
import typer

app = typer.Typer()


@app.command()
def validate(name: str):
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


def main():
    app()
