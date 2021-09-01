# def parse(args=None, namespace=None):
#     import argparse
#     import sys

#     # create the top-level parser
#     parser = argparse.ArgumentParser(prog="npe2")
#     subparsers = parser.add_subparsers()

#     # create the parser for the "validate" command
#     parse_validate = subparsers.add_parser(
#         "validate", help="validate manifest for a path or package"
#     )
#     parse_validate.add_argument(
#         "path", type=str, nargs="+", help="Manifest file or package to validate"
#     )

#     return parser.parse_args(args=None, namespace=None)

# def main():
#     args = NPEParser().parse_args()
#     print(args)

from typing import Tuple
import typer

app = typer.Typer()


def _validate(package_or_filename: str) -> Tuple[bool, str]:
    from npe2 import PluginManifest
    from pydantic import ValidationError

    pm = None
    verr = None
    err = None

    try:
        pm = PluginManifest.from_file(package_or_filename)
    except ValidationError as e:
        verr = e
    except Exception as e:
        err = e

    if pm is None and verr is None:
        try:
            pm = PluginManifest.from_distribution(package_or_filename)
        except ValidationError as e:
            verr = e
        except Exception as e:
            err = e

    if pm is None:
        if verr is not None:
            msg = f"🅇 Invalid! {verr}"
        else:
            msg = (
                f"🅇 Failed to load {package_or_filename!r}. {type(err).__name__}: {err}"
            )
        return False, msg

    return True, f"✔ Manifest for {pm.display_name!r} valid!"


@app.command()
def validate(name: str):
    """Validate manifest for a distribution name or manifest filepath."""
    valid, msg = _validate(name)
    color = typer.colors.GREEN if valid else typer.colors.RED
    typer.echo(typer.style(msg, fg=color, bold=True))


@app.command()
def parse(name: str):
    print(type(name))
    typer.echo(f"Hello {name}")


def main():
    app()
