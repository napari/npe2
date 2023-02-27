import builtins
import sys
import warnings
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, List, Optional, Sequence

import typer

from npe2 import PluginManager, PluginManifest, __version__

if TYPE_CHECKING:
    from rich.console import RenderableType

app = typer.Typer(no_args_is_help=True)


def _show_version_and_exit(value: bool) -> None:
    if value:
        typer.echo(f"npe2 v{__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=_show_version_and_exit,
        help="Show version and exit.",
        is_eager=True,
    ),
):
    """npe2: napari plugin engine (v{version})

    For additional help on a specific command: type 'npe2 [command] --help'
    """


_main.__doc__ = typer.style(
    (_main.__doc__ or "").format(version=__version__), fg="bright_yellow"
)

SYNTAX_THME = "monokai"
SYNTAX_BACKGROUND = "black"


class Format(str, Enum):
    """Valid manifest file formats."""

    yaml = "yaml"
    json = "json"
    toml = "toml"


class ListFormat(str, Enum):
    """Valid out formats for `npe2 list`."""

    table = "table"
    json = "json"  # alias for json in pandas "records" format
    yaml = "yaml"
    compact = "compact"


def _pprint_formatted(string, format: Format = Format.yaml):  # pragma: no cover
    """Print yaml nicely, depending on available modules."""
    from rich.console import Console
    from rich.syntax import Syntax

    syntax = Syntax(
        string, format.value, theme=SYNTAX_THME, background_color=SYNTAX_BACKGROUND
    )
    Console().print(syntax)


def _pprint_exception(err: Exception):
    from rich.console import Console
    from rich.traceback import Traceback

    e_info = (type(err), err, err.__traceback__)

    trace = Traceback.extract(*e_info, show_locals=True)
    Console().print(Traceback(trace))


def _pprint_table(
    headers: Sequence["RenderableType"], rows: Sequence[Sequence["RenderableType"]]
):
    from itertools import cycle

    from rich.console import Console
    from rich.table import Table

    COLORS = ["cyan", "magenta", "green", "yellow"]
    EMOJI_TRUE = ":white_check_mark:"
    EMOJI_FALSE = ""

    table = Table()
    for head, color in zip(headers, cycle(COLORS)):
        table.add_column(head, style=color)
    for row in rows:
        strings = []
        for r in row:
            val = ""
            if isinstance(r, dict):
                val = ", ".join(f"{k} ({v})" for k, v in r.items())
            elif r:
                val = str(r).replace("True", EMOJI_TRUE).replace("False", EMOJI_FALSE)
            strings.append(val)
        table.add_row(*strings)

    console = Console()
    console.print(table)


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


def _make_rows(pm_dict: dict, normed_fields: Sequence[str]) -> Iterator[List]:
    """Cleanup output from pm.dict() into rows for table.

    outside of just extracting the fields we care about, this also:

    - handles nested fields expressed as dotted strings: `packge_metadata.version`
    - negates fields that are prefixed with `!`
    - simplifies contributions to a {name: count} dict.

    """
    for info in pm_dict["plugins"].values():
        row = []
        for field in normed_fields:
            val = info.get(field.lstrip("!"))

            # extact nested fields
            if not val and "." in field:
                parts = field.split(".")
                val = info
                while parts and hasattr(val, "__getitem__"):
                    val = val[parts.pop(0)]

            # negate fields starting with !
            if field.startswith("!"):
                val = not val

            # simplify contributions to just the number of contributions
            if field == "contributions":
                val = {k: len(v) for k, v in val.items() if v}

            row.append(val)
        yield row


@app.command()
def list(
    fields: str = typer.Option(
        "name,version,npe2,contributions",
        help="Comma seperated list of fields to include in the output."
        "Names may contain dots, indicating nested manifest fields "
        "(`contributions.readers`). Fields names prefixed with `!` will be "
        "negated in the output. Fields will appear in the table in the order in "
        "which they are provided.",
        metavar="FIELDS",
    ),
    sort: str = typer.Option(
        "0",
        "-s",
        "--sort",
        help="Field name or (int) index on which to sort.",
        metavar="KEY",
    ),
    format: ListFormat = typer.Option(
        "table",
        "-f",
        "--format",
        help="Out format to use. When using 'compact', `--fields` is ignored ",
    ),
):
    """List currently installed plugins."""

    if format == ListFormat.compact:
        fields = "name,version,contributions"

    requested_fields = [f.lower() for f in fields.split(",")]

    # check for sort values that will not work
    bad_sort_param_msg = (
        f"Invalid sort value {sort!r}. "
        f"Must be column index (<{len(requested_fields)}) or one of: "
        + ", ".join(requested_fields)
    )
    try:
        if (sort_index := int(sort)) >= len(requested_fields):
            raise typer.BadParameter(bad_sort_param_msg)
    except ValueError:
        try:
            sort_index = requested_fields.index(sort.lower())
        except ValueError as e:
            raise typer.BadParameter(bad_sort_param_msg) from e

    # some convenience aliases
    ALIASES = {
        "version": "package_metadata.version",
        "summary": "package_metadata.summary",
        "license": "package_metadata.license",
        "author": "package_metadata.author",
        "npe2": "!npe1_shim",
        "npe1": "npe1_shim",
    }
    normed_fields = [ALIASES.get(f, f) for f in requested_fields]

    pm = PluginManager.instance()
    pm.discover(include_npe1=True)
    pm.index_npe1_adapters()
    pm_dict = pm.dict(include={f.lstrip("!") for f in normed_fields})
    rows = sorted(_make_rows(pm_dict, normed_fields), key=lambda r: r[sort_index])

    if format == ListFormat.table:
        heads = [f.split(".")[-1].replace("_", " ").title() for f in requested_fields]
        _pprint_table(headers=heads, rows=rows)
        return

    # standard records format used for the other formats
    # [{column -> value}, ... , {column -> value}]
    data: List[dict] = [dict(zip(requested_fields, row)) for row in rows]

    if format == ListFormat.json:
        import json

        _pprint_formatted(json.dumps(data, indent=1), Format.json)
    elif format in (ListFormat.yaml):
        import yaml

        _pprint_formatted(yaml.safe_dump(data, sort_keys=False), Format.yaml)
    elif format in (ListFormat.compact):
        template = "  - {name}: {version} ({ncontrib} contributions)"
        for r in data:
            ncontrib = sum(r.get("contributions", {}).values())
            typer.echo(template.format(**r, ncontrib=ncontrib))


def _fetch_all_manifests(doit: bool):
    """Fetch all manifests and dump to "manifests" folder."""
    if not doit:
        return

    from npe2._inspection import _fetch

    dest = "manifests"
    if "-o" in sys.argv:
        dest = sys.argv[sys.argv.index("-o") + 1]
    elif "--output" in sys.argv:  # pragma: no cover
        dest = sys.argv[sys.argv.index("--output") + 1]

    _fetch.fetch_all_manifests(dest)
    raise typer.Exit(0)


@app.command()
def fetch(
    name: List[str],
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
    all: Optional[bool] = typer.Option(
        None,
        "--all",
        help="Fetch manifests for ALL known plugins (will be SLOW)",
        callback=_fetch_all_manifests,
        is_eager=True,
    ),
):
    """Fetch manifest from remote package.

    If an npe2 plugin is detected, the manifest is returned directly, otherwise
    it will be installed into a temporary directory, imported, and discovered.
    """
    from npe2 import fetch_manifest

    fmt = _check_output(output) if output else format
    kwargs: dict = {"indent": indent}
    if include_package_meta:
        kwargs["exclude"] = set()

    for n in name:
        mf = fetch_manifest(n, version=version)
        manifest_string = getattr(mf, fmt.value)(**kwargs)

        if output:
            output.write_text(manifest_string, encoding="utf-8")
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
    from ._inspection._from_npe1 import convert_repository, manifest_from_npe1

    try:
        with warnings.catch_warnings(record=True) as w:
            if path.is_dir():
                pm, mf_path = convert_repository(path, dry_run=dry_run)
            else:
                pm = manifest_from_npe1(str(path))
        if w:
            from textwrap import indent

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
        raise typer.Exit(1) from e

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
        if _cleared := clear_cache(names):
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


@app.command()
def compile(
    src_dir: str,
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        exists=False,
        help="If provided, will write manifest to filepath (must end with .yaml, "
        ".json, or .toml). Otherwise, will print to stdout.",
    ),
    format: Format = typer.Option(
        "yaml", "-f", "--format", help="Markdown format to use."
    ),
):
    """Compile @npe2.implements contributions to generate a manifest."""
    from . import _inspection

    manifest = _inspection.compile(src_dir, dest=output)
    manifest_string = getattr(manifest, format.value)(indent=2)
    _pprint_formatted(manifest_string, format)


def main():
    app()
