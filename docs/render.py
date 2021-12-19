from __future__ import annotations

import json
from collections import namedtuple
from functools import lru_cache
from inspect import getsource
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Dict, Sequence, Tuple, Union

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from typing_extensions import get_origin

from npe2.manifest import PluginManifest
from npe2.manifest.contributions import ContributionPoints
from npe2.manifest.utils import Executable

if TYPE_CHECKING:
    from pydantic.fields import ModelField

DOCS = Path(__file__).parent
TEMPLATES = DOCS / "templates"
_BUILD = DOCS / "_build"
EXAMPLE = PluginManifest.from_file(DOCS / "example_manifest.yaml")

Contrib = namedtuple("Contrib", "name doc fields union_fields example")
UnionField = namedtuple("UnionField", "doc fields")


def _extract_example(field: ModelField, example: PluginManifest = EXAMPLE):
    # present example for just this field
    assert example.contributions
    contribs = getattr(example.contributions, field.name)
    # only take the first command example ... the rest are for executables
    if field.name == "commands":
        contribs = [contribs[0]]

    ex = ContributionPoints(**{field.name: contribs})
    # for "executables", include associated command
    ExampleCommands = example.contributions.commands
    assert ExampleCommands
    for c in contribs or ():
        if isinstance(c, Executable):
            associated_command = next(i for i in ExampleCommands if i.id == c.command)
            if not ex.commands:
                ex.commands = []
            ex.commands.append(associated_command)
    return yaml.safe_dump({"contributions": json.loads(ex.json(exclude_unset=True))})


def _get_fields(
    field: ModelField,
) -> Tuple[str, Sequence[ModelField], Sequence[ModelField]]:
    field_type = field.type_
    union_fields = []
    if get_origin(field.type_) == Union:
        base = _common_base(*field_type.__args__)
        assert base
        for subf in field_type.__args__:
            fields = [
                f for f in subf.__fields__.values() if f.name not in base.__fields__
            ]
            union_fields.append(UnionField(_model_doc(subf), fields))
        field_type = base

    doc = _model_doc(field_type)
    fields = field_type.__fields__.values()
    return doc, fields, union_fields


def _model_doc(field_type):
    return dedent("    " + (field_type.__doc__ or ""))


def _common_base(*classes):
    from itertools import product

    for a, b in product(*(c.__mro__ for c in classes)):
        if a is b:
            return a
    return None


def _iter_visible_contribution_points():
    for field in ContributionPoints.__fields__.values():
        if field.name not in getattr(ContributionPoints.__config__, "docs_exclude", {}):
            yield field


def _get_contributions():
    return [
        Contrib(field.name, *_get_fields(field), _extract_example(field))
        for field in _iter_visible_contribution_points()
    ]


def _get_specs():
    specs = {}
    for field in _iter_visible_contribution_points():
        field_type = field.type_
        config = getattr(field_type, "__config__", None)
        if not config:
            continue
        spec = getattr(config, "reference_spec", None)
        if spec:

            specs[field_type.__name__] = get_spec_source(spec)
    return specs


@lru_cache
def type_strings() -> Dict[str, str]:
    from npe2 import types as _t

    type_strings = {}
    type_lines = getsource(_t).splitlines()
    for r, line in enumerate(type_lines):
        if not line or line.startswith((" ", "#", "]", "if", "from")):
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


def get_spec_source(spec) -> str:
    import inspect

    source = inspect.getsource(spec)
    for name in spec.__code__.co_names:
        if name in spec.__globals__:
            f = spec.__globals__[name]
            source += "\n\n" + inspect.getsource(f)

    needed = _get_needed_types(source)
    lines = [v for k, v in type_strings().items() if k in needed]
    if lines:
        lines.extend(["", ""])
    lines.extend(source.splitlines())
    return "\n".join(lines)


def _get_needed_types(source: str, so_far=set()):
    for name, string in type_strings().items():
        # we treat LayerData specially
        if name in source and name != "LayerData" and name not in so_far:
            so_far.add(name)
            so_far.update(_get_needed_types(string, so_far=so_far))
    return so_far


def main(dest: Path = _BUILD):
    env = Environment(loader=PackageLoader("docs"), autoescape=select_autoescape())
    dest.mkdir(exist_ok=True, parents=True)
    context = {
        "contributions": _get_contributions(),
        "schema": PluginManifest.schema(),
        "example": EXAMPLE,
        "specs": _get_specs(),
    }
    for t in TEMPLATES.glob("*.jinja"):
        template = env.get_template(t.name)
        _dest = dest / f"{t.stem}"
        _dest.write_text(template.render(context))
        print(f"Rendered {_dest}")


if __name__ == "__main__":
    main()
