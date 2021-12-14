import json
import typing
from collections import namedtuple
from pathlib import Path
from textwrap import dedent

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from npe2.manifest import PluginManifest
from npe2.manifest.contributions import ContributionPoints

DOCS = Path(__file__).parent
Example = PluginManifest.from_file(
    DOCS.parent / "tests" / "sample" / "my_plugin" / "napari.yaml"
)


TEMPLATES = DOCS / "templates"
_BUILD = DOCS / "_build"


Contrib = namedtuple("Contrib", "name doc example, fields")
contributions = []
for name, v in ContributionPoints.__fields__.items():
    doc = dedent("    " + (v.type_.__doc__ or ""))
    example = getattr(Example.contributions, name)
    if isinstance(example, list):
        example = example[0]

    field_type = v.type_
    if typing.get_origin(field_type) == typing.Union:
        # TODO: iterate
        field_type = field_type.__args__[0]

    fields = field_type.__fields__.values()
    example = yaml.safe_dump(json.loads(example.json(exclude_unset=True)))
    contributions.append(Contrib(name, doc, example, fields))


def main():
    env = Environment(loader=PackageLoader("docs"), autoescape=select_autoescape())
    _BUILD.mkdir(exist_ok=True, parents=True)
    suffix = ".md"
    for t in TEMPLATES.glob("*.jinja"):
        template = env.get_template(t.name)
        context = {
            "contributions": contributions,
            "example": Example,
        }
        (_BUILD / f"{t.stem}{suffix}").write_text(template.render(context))


if __name__ == "__main__":
    main()
