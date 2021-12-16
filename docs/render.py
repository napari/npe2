import json
import typing
from collections import namedtuple
from pathlib import Path
from textwrap import dedent

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from npe2.manifest import PluginManifest
from npe2.manifest.contributions import ContributionPoints
from npe2.manifest.utils import Executable

DOCS = Path(__file__).parent
Example = PluginManifest.from_file(DOCS / "example_manfest.yaml")
ExampleCommands = Example.contributions.commands  # type: ignore

TEMPLATES = DOCS / "templates"
_BUILD = DOCS / "_build"


Contrib = namedtuple("Contrib", "name doc example, fields")
contributions = []
for name, v in ContributionPoints.__fields__.items():
    doc = dedent("    " + (v.type_.__doc__ or ""))

    field_type = v.type_
    if typing.get_origin(field_type) == typing.Union:
        # TODO: iterate
        field_type = field_type.__args__[0]

    fields = field_type.__fields__.values()

    # present example for just this field
    contribs = getattr(Example.contributions, name)

    # only take the first command example ... the rest are for executables
    if name == "commands":
        contribs = [contribs[0]]

    ex = ContributionPoints(**{name: contribs})
    # for "executables", include associated command
    for c in contribs or ():
        if isinstance(c, Executable):
            associated_command = next(
                i for i in ExampleCommands if i.id == c.command  # type: ignore
            )
            if not ex.commands:
                ex.commands = []
            ex.commands.append(associated_command)
    ex = yaml.safe_dump({"contributions": json.loads(ex.json(exclude_unset=True))})
    contributions.append(Contrib(name, doc, ex, fields))


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
