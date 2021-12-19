from __future__ import annotations

import json
from collections import namedtuple
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Sequence, Tuple, Union

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
EXAMPLE = PluginManifest.from_file(DOCS / "example_manfest.yaml")

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


def _get_contributions():
    return [
        Contrib(field.name, *_get_fields(field), _extract_example(field))
        for field in ContributionPoints.__fields__.values()
        if field.name not in getattr(ContributionPoints.__config__, "docs_exclude", {})
    ]


def main():
    env = Environment(loader=PackageLoader("docs"), autoescape=select_autoescape())
    _BUILD.mkdir(exist_ok=True, parents=True)
    for t in TEMPLATES.glob("*.jinja"):
        template = env.get_template(t.name)
        context = {
            "contributions": _get_contributions(),
            "schema": PluginManifest.schema(),
            "example": EXAMPLE,
        }
        (_BUILD / f"{t.stem}").write_text(template.render(context))


if __name__ == "__main__":
    main()
