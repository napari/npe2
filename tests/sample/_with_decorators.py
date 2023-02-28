# mypy: disable-error-code=empty-body
"""This module mimics all of the contributions my-plugin...
but is used to reverse-engineer the manifest."""
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

# to test various ways that this can be imported, since we're using static parsing.
import npe2.implements
import npe2.implements as impls
from npe2 import implements
from npe2.implements import reader

# alternative pattern that does not require npe2 at runtime
if TYPE_CHECKING:
    from npe2 import implements as noimport
else:
    # create no-op `implements.anything(**kwargs)` decorator
    D = type("D", (), {"__getattr__": lambda *_: (lambda **_: (lambda f: f))})
    noimport = D()


@implements.on_activate
def activate(ctx):
    ...


@implements.on_deactivate
def deactivate(ctx):
    ...


@implements.reader(
    id="some_reader",
    title="Some Reader",
    filename_patterns=["*.fzy", "*.fzzy"],
    accepts_directories=True,
)
def get_reader(path: str):
    ...


@reader(
    id="url_reader",
    title="URL Reader",
    filename_patterns=["http://*", "https://*"],
    accepts_directories=False,
    ensure_args_valid=True,
)
def url_reader(path: str):
    ...


@noimport.writer(
    id="my_writer",
    title="My Multi-layer Writer",
    filename_extensions=["*.tif", "*.tiff"],
    layer_types=["image{2,4}", "tracks?"],
)
@implements.writer(
    id="my_writer",
    title="My Multi-layer Writer",
    filename_extensions=["*.pcd", "*.e57"],
    layer_types=["points{1}", "surface+"],
)
def writer_function(path: str, layer_data: List[Tuple[Any, Dict, str]]) -> List[str]:
    ...


@implements.writer(
    id="my_single_writer",
    title="My single-layer Writer",
    filename_extensions=["*.xyz"],
    layer_types=["labels"],
)
def writer_function_single(path: str, layer_data: Any, meta: Dict) -> List[str]:
    ...


@npe2.implements.widget(
    id="some_widget", title="Create my widget", display_name="My Widget"
)
class SomeWidget:
    ...


@npe2.implements.sample_data_generator(
    id="my-plugin.generate_random_data",  # the plugin-name is optional
    title="Generate uniform random data",
    key="random_data",
    display_name="Some Random Data (512 x 512)",
)
def random_data():
    ...


@impls.widget(
    id="some_function_widget",
    title="Create widget from my function",
    display_name="A Widget From a Function",
    autogenerate=True,
)
def make_widget_from_function(x: int, threshold: int):
    ...
