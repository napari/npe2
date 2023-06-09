from __future__ import annotations

import inspect
import json
import os
import re
import sys
from contextlib import contextmanager
from functools import lru_cache, partial
from inspect import getsource
from pathlib import Path
from types import FunctionType
from typing import Dict, Optional, Set
from urllib.request import urlopen

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from npe2 import PluginManager, PluginManifest
from npe2.manifest.contributions import ContributionPoints
from npe2.manifest.utils import Executable

SCHEMA_URL = "https://github.com/napari/npe2/releases/latest/download/schema.json"
DOCS = Path(__file__).parent
TEMPLATES = DOCS / "templates"
_BUILD = DOCS.parent / "docs" / "plugins"
EXAMPLE_MANIFEST = PluginManifest.from_file(DOCS / "example_manifest.yaml")


@contextmanager
def _mocked_qtwidgets():
    # just mocking a "qtpy.QtWidgets" so we don't need to include PyQt just to build
    # documentation.
    from types import ModuleType

    mock = ModuleType("qtpy.QtWidgets")
    mock.__dict__["QWidget"] = object
    before, sys.modules["qtpy.QtWidgets"] = sys.modules.get("qtpy.QtWidgets"), mock
    try:
        yield
    finally:
        if before is not None:
            sys.modules["qtpy.QtWidgets"] = mock
        else:
            del sys.modules["qtpy.QtWidgets"]


@lru_cache
def type_strings() -> Dict[str, str]:
    """Return map of type name to source code for all types in types.py"""
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


def _get_needed_types(source: str, so_far: Optional[Set[str]] = None) -> Set[str]:
    """Return the names of types in the npe2.types.py that are used in `source`"""
    so_far = so_far or set()
    for name, string in type_strings().items():
        # we treat LayerData specially
        if (
            name != "LayerData"
            and name not in so_far
            and re.search(rf"\W{name}\W", source)
        ):
            so_far.add(name)
            so_far.update(_get_needed_types(string, so_far=so_far))
    return so_far


def _build_example(contrib: Executable) -> str:
    """Extract just the source code for a specific executable contribution"""

    if not isinstance(contrib, Executable):
        return ""

    with _mocked_qtwidgets():
        func = contrib.get_callable()

    if not callable(func):
        return ""
    if isinstance(func, partial):
        func = func.keywords["function"]
    source = inspect.getsource(func)

    # additionally get source code of all internally referenced functions
    # i.e. for get_reader we also get the source for the returned reader.
    if isinstance(func, FunctionType):
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
    """Build an example string of python source implementing a specific contribution."""
    contrib = getattr(EXAMPLE_MANIFEST.contributions, contrib_name)
    if isinstance(contrib, list):
        return "\n\n".join([_build_example(x) for x in contrib]).strip()
    return _build_example(contrib)


def example_contribution(
    contrib_name: str, format="yaml", manifest: PluginManifest = EXAMPLE_MANIFEST
) -> str:
    """Get small manifest example for just contribution named `contrib_name`"""
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
        import tomli_w

        return tomli_w.dumps(output)
    if format == "json":
        return json.dumps(output)
    raise ValueError("Invalid format: {format}.  Must be 'yaml', 'toml' or 'json'.")


def has_guide(contrib_name: str) -> bool:
    """Return true if a guide exists for this contribution."""
    return (TEMPLATES / f"_npe2_{contrib_name}_guide.md.jinja").exists()


def main(dest: Path = _BUILD):
    """Render all jinja docs in ./templates and output to `dest`"""

    # register the example plugin so we can use `.get_callable()` in _build_example
    sys.path.append(str(DOCS.absolute()))
    PluginManager.instance().register(EXAMPLE_MANIFEST)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape()
    )
    env.filters["example_contribution"] = example_contribution
    env.filters["example_implementation"] = example_implementation
    env.filters["has_guide"] = has_guide

    dest.mkdir(exist_ok=True, parents=True)
    schema = PluginManifest.schema()
    if local_schema := os.getenv("NPE2_SCHEMA"):
        with open(local_schema) as f:
            schema = json.load(f)
    else:
        with urlopen(SCHEMA_URL) as response:
            schema = json.load(response)

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
        _dest.write_text(template.render(context), encoding="utf-8")
        print(f"Rendered {_dest}")


if __name__ == "__main__":
    dest = Path(sys.argv[1]).absolute() if len(sys.argv) > 1 else _BUILD
    main(dest)
