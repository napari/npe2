from __future__ import annotations

import json
import re
from functools import lru_cache
from inspect import getsource
from pathlib import Path
from typing import Dict

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from npe2 import PluginManager
from npe2.manifest import PluginManifest
from npe2.manifest.contributions import ContributionPoints
from npe2.manifest.schema import _temporary_path_additions
from npe2.manifest.utils import Executable

DOCS = Path(__file__).parent
TEMPLATES = DOCS / "templates"
_BUILD = DOCS / "_build"
EXAMPLE_MANIFEST = PluginManifest.from_file(DOCS / "example_manifest.yaml")
with _temporary_path_additions([str(DOCS.absolute())]):
    pass
PluginManager.instance().register(EXAMPLE_MANIFEST)


@lru_cache
def type_strings() -> Dict[str, str]:
    from npe2 import types as _t

    type_strings = {}
    type_lines = getsource(_t).splitlines()
    for r, line in enumerate(type_lines):
        if not line or line.startswith((" ", "#", "]", ")", "if", "from")):
            continue
        end = 0
        if r + 1 >= len(type_lines):
            continue
        next_line = type_lines[r + 1]
        if next_line.startswith(" "):
            end = next(
                (
                    i
                    for i, x in enumerate(type_lines[r + 1 :])
                    if not x.startswith((" ", "#"))
                )
            )
        if end:
            end += 1
        name = line.split()[0]
        if name == "class":
            name = line.split()[1].split("(")[0]
        type_strings[name] = "\n".join(type_lines[r : r + end + 1])
    return type_strings


def _build_example(contrib) -> str:
    import inspect

    from magicgui._magicgui import MagicFactory

    if not hasattr(contrib, "get_callable"):
        return ""
    func = contrib.get_callable()
    if not callable(func):
        return ""
    if isinstance(func, MagicFactory):
        func = func.keywords["function"]
    source = inspect.getsource(func)
    if hasattr(func, "__code__"):
        for name in func.__code__.co_names:
            if name in func.__globals__:
                f = func.__globals__[name]
                source += "\n\n" + inspect.getsource(f)

    needed = _get_needed_types(source)
    lines = [v for k, v in type_strings().items() if k in needed]
    if lines:
        lines.extend(["", ""])
    lines.extend(source.splitlines())
    return "\n".join(lines)


def example_implementation(contrib_name: str) -> str:

    contrib = getattr(EXAMPLE_MANIFEST.contributions, contrib_name)
    if isinstance(contrib, list):
        return "\n\n".join([_build_example(x) for x in contrib]).strip()
    return _build_example(contrib)


def _get_needed_types(source: str, so_far=None):
    so_far = so_far or set()
    for name, string in type_strings().items():
        # we treat LayerData specially
        if (
            name != "LayerData"
            and name not in so_far
            and re.search(fr"\W{name}\W", source)
        ):
            so_far.add(name)
            so_far.update(_get_needed_types(string, so_far=so_far))
    return so_far


def example_contribution(
    contrib_name: str, format="yaml", manifest: PluginManifest = EXAMPLE_MANIFEST
) -> str:
    """Get small example for just this `contrib_name`"""
    assert manifest.contributions
    contribs = getattr(manifest.contributions, contrib_name)
    # only take the first command example ... the rest are for executables
    if contrib_name == "commands":
        contribs = [contribs[0]]

    ex = ContributionPoints(**{contrib_name: contribs})
    # for "executables", include associated command
    ExampleCommands = manifest.contributions.commands
    assert ExampleCommands
    for c in contribs or ():
        if isinstance(c, Executable):
            associated_command = next(i for i in ExampleCommands if i.id == c.command)
            if not ex.commands:
                ex.commands = []
            ex.commands.append(associated_command)
    output = {"contributions": json.loads(ex.json(exclude_unset=True))}
    if format == "yaml":
        return yaml.safe_dump(output, sort_keys=False)
    if format == "toml":
        import pytomlpp as toml

        return toml.dumps(output)
    if format == "json":
        return json.dumps(output)
    raise ValueError("Invalid format: {format}.  Must be 'yaml', 'toml' or 'json'.")


def main(dest: Path = _BUILD):
    this = Path(__file__).parent.name
    env = Environment(loader=PackageLoader(this), autoescape=select_autoescape())
    env.filters["example_contribution"] = example_contribution
    env.filters["example_implementation"] = example_implementation

    dest.mkdir(exist_ok=True, parents=True)
    schema = PluginManifest.schema()
    contributions = schema["definitions"]["ContributionPoints"]["properties"]
    context = {
        "schema": schema,
        "contributions": contributions,
        "example": EXAMPLE_MANIFEST,
        # "specs": _get_specs(),
        "specs": {},
    }
    for t in TEMPLATES.glob("*.jinja"):
        template = env.get_template(t.name)
        _dest = dest / f"{t.stem}"
        _dest.write_text(template.render(context))
        print(f"Rendered {_dest}")


if __name__ == "__main__":
    import sys

    dest = Path(sys.argv[1]).absolute() if len(sys.argv) > 1 else _BUILD
    main(dest)
