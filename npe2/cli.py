import builtins
import warnings
from enum import Enum
from pathlib import Path
from textwrap import indent
from typing import List, Optional

import typer

from npe2 import PluginManifest

app = typer.Typer()


class Format(str, Enum):
    """Valid manifest file formats."""

    yaml = "yaml"
    json = "json"
    toml = "toml"


def _pprint_formatted(string, format: Format = Format.yaml):  # pragma: no cover
    """Print yaml nicely, depending on available modules."""
    try:
        from rich.console import Console
        from rich.syntax import Syntax

        Console().print(Syntax(string, format.value, theme="fruity"))
    except ImportError:
        typer.echo(string)


def _pprint_exception(err: Exception):
    e_info = (type(err), err, err.__traceback__)
    try:
        from rich.console import Console
        from rich.traceback import Traceback

        trace = Traceback.extract(*e_info, show_locals=True)
        Console().print(Traceback(trace))
    except ImportError:
        import traceback

        typer.echo("\n" + "".join(traceback.format_exception(*e_info)))


@app.command()
def validate(
    name: str,
    imports: bool = typer.Option(
        False,
        help="Validate all `python_name` entries by importing. This runs python code! "
        "package must be importable on sys.path.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print tracebacks on error.",
    ),
):
    """Validate manifest for a distribution name or manifest filepath."""

    err: Optional[Exception] = None
    try:
        pm = PluginManifest._from_package_or_name(name)
        msg = f"✔ Manifest for {(pm.display_name or pm.name)!r} valid!"
        if imports:
            pm.validate_imports()
    except PluginManifest.ValidationError as e:
        msg = f"🅇 Invalid! {e}"
        err = e
    except Exception as e:
        msg = f"🅇 Unexpected error in {name!r}.\n{type(e).__name__}: {e}"
        err = e

    typer.secho(msg, fg=typer.colors.RED if err else typer.colors.GREEN, bold=True)
    if err is not None:
        if debug:
            _pprint_exception(err)

        raise typer.Exit(1)


def _check_output(output: Path) -> Format:
    if output.suffix.lstrip(".") not in Format._member_names_:
        typer.echo(
            f"Invalid output extension {output.suffix!r}. Must be one of: "
            + ", ".join(Format._member_names_)
        )
        raise typer.Exit(1)
    return Format(output.suffix.lstrip("."))


@app.command()
def parse(
    name: str = typer.Argument(
        ..., help="Name of an installed package, or path to a manifest file."
    ),
    format: Format = typer.Option(
        "yaml", "-f", "--format", help="Markdown format to use."
    ),
    indent: Optional[int] = typer.Option(
        None,
        "--indent",
        help="Number of spaces to indent (for json)",
        min=0,
        max=10,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        exists=False,
        help="If provided, will write manifest to filepath (must end with .yaml, "
        ".json, or .toml). Otherwise, will print to stdout.",
    ),
):
    """Show parsed manifest as yaml."""
    fmt = _check_output(output) if output else format
    pm = PluginManifest._from_package_or_name(name)
    manifest_string = getattr(pm, fmt.value)(indent=indent)
    if output:
        output.write_text(manifest_string)
    else:
        _pprint_formatted(manifest_string, fmt)


@app.command()
def fetch(
    name: str,
    version: Optional[str] = None,
    include_package_meta: Optional[bool] = typer.Option(
        False,
        "-m",
        "--include-package-meta",
        help="Include package metadata in the manifest.",
    ),
    format: Format = typer.Option(
        "yaml", "-f", "--format", help="Markdown format to use."
    ),
    indent: Optional[int] = typer.Option(
        None,
        "--indent",
        help="Number of spaces to indent (for json)",
        min=0,
        max=10,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        exists=False,
        help="If provided, will write manifest to filepath (must end with .yaml, "
        ".json, or .toml). Otherwise, will print to stdout.",
    ),
):
    """Fetch manifest from remote package.

    If an npe2 plugin is detected, the manifest is returned directly, otherwise
    it will be installed into a temporary directory, imported, and discovered.
    """
    from npe2._fetch import fetch_manifest

    fmt = _check_output(output) if output else format
    kwargs: dict = {"indent": indent}
    if include_package_meta:
        kwargs["exclude"] = set()

    mf = fetch_manifest(name, version=version)
    manifest_string = getattr(mf, fmt.value)(**kwargs)

    if output:
        output.write_text(manifest_string)
    else:
        _pprint_formatted(manifest_string, fmt)


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
            typer.echo()

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
        _pprint_formatted(pm.yaml(), Format.yaml)
    else:
        msg = f"✔  Conversion complete! New manifest at {mf_path}."
        typer.secho(msg, fg=typer.colors.GREEN, bold=True)
        typer.secho(
            "If you have any napari_plugin_engine imports or hook_implementation "
            "decorators, you may remove them now.",
            fg=typer.colors.GREEN,
            bold=False,
        )


@app.command()
def cache(
    clear: Optional[bool] = typer.Option(
        False, "--clear", "-d", help="Clear the npe1 adapter manifest cache"
    ),
    names: List[str] = typer.Argument(
        None, help="Name(s) of distributions to list/delete"
    ),
    list_: Optional[bool] = typer.Option(
        False, "--list", "-l", help="List cached manifests"
    ),
    verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="verbose"),
):
    """Cache utils"""
    from npe2.manifest._npe1_adapter import ADAPTER_CACHE, clear_cache

    if clear:
        _cleared = clear_cache(names)
        if _cleared:
            nf = "\n".join(f" - {i.name}" for i in _cleared)
            typer.secho("Cleared these files from cache:")
            typer.secho(nf, fg=typer.colors.RED)
        else:
            msg = "Nothing to clear"
            if names:
                msg += f" for plugins: {','.join(names)}"
            typer.secho(msg, fg=typer.colors.RED)

        typer.Exit()
    if list_:
        files = builtins.list(ADAPTER_CACHE.glob("*.yaml"))
        if names:
            files = [f for f in files if any(f.name.startswith(n) for n in names)]

        if not files:
            if names:
                typer.secho(f"Nothing cached for plugins: {','.join(names)}")
            else:
                typer.secho("Nothing cached")
            typer.Exit()
        for fname in files:
            mf = PluginManifest.from_file(fname)
            if verbose:
                _pprint_formatted(mf.yaml(), Format.yaml)  # pragma: no cover
            else:
                typer.secho(f"{mf.name}: {mf.package_version}", fg=typer.colors.GREEN)


def main():
    app()
