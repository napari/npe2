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


@app.command()
def convert(name: str, out: Optional[str] = None):
    """Convert existing plugin to new manifest"""

    mf = create_manifest(name)
    if out is not None:
        with open(out, "w") as fh:
            fh.write(mf)
    else:
        print(mf)


def create_manifest(plugin_name: str) -> str:
    """function that takes plugin name and exports manifest"""

    from .conversion import plugin_manager

    # from napari.plugins import plugin_manager as plugin_manager

    plugin_manager.discover()

    if plugin_name not in plugin_manager.plugins:
        raise ValueError("Could not find plugin", plugin_name)

    module = plugin_manager.plugins[plugin_name]
    standard_meta = plugin_manager.get_standard_metadata(plugin_name)
    package = standard_meta["package"].replace("-", "_")

    commands = []
    for caller in plugin_manager._plugin2hookcallers[module]:
        for impl in caller.get_hookimpls():
            if impl.plugin_name != plugin_name:
                continue
            name = impl.specname.replace("napari_", "")
            id = f"{package}.{name}"
            python_name = f"{impl.function.__module__}:{impl.function.__qualname__}"
            title = " ".join(name.split("_")).title()
            commands.append({"id": id, "python_name": python_name, "title": title})

    pm = PluginManifest(
        name=package,
        publisher=standard_meta["author"],
        description=standard_meta["summary"],
        version=standard_meta["version"],
        contributions={"commands": commands},
    )
    return pm.yaml()


def main():
    app()
