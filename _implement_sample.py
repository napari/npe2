from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from pydantic import BaseModel

import npe2.implements
import npe2.implements as impls
from npe2 import PluginContext, implements

if TYPE_CHECKING:
    import napari.types


@implements.on_activate
def activate(context: PluginContext):
    @context.register_command("my_plugin.hello_world")
    def _hello():
        ...

    context.register_command("my_plugin.another_command", lambda: print("yo!"))


@implements.on_deactivate
def deactivate(context: PluginContext):
    """just here for tests"""


@implements.reader(
    id="some_reader",
    title="Some Reader",
    filename_patterns=["*.fzy", "*.fzzy"],
    accepts_directories=True,
)
def get_reader(path: str):
    if path.endswith(".fzzy"):

        def read(path):
            return [(None,)]

        return read


@implements.reader(
    id="url_reader", title="URL Reader", filename_patterns=["http://*", "https://*"]
)
def url_reader(path: str):
    if path.startswith("http"):

        def read(path):
            return [(None,)]

        return read


@implements.writer(
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
    class Arg(BaseModel):
        data: Any
        meta: Dict
        layer_type: str

    for e in layer_data:
        Arg(data=e[0], meta=e[1], layer_type=e[2])

    return [path]


@implements.writer(
    id="my_single_writer",
    title="My single-layer Writer",
    filename_extensions=["*.xyz"],
    layer_types=["labels"],
)
def writer_function_single(path: str, layer_data: Any, meta: Dict) -> List[str]:
    class Arg(BaseModel):
        data: Any
        meta: Dict

    Arg(data=layer_data, meta=meta)

    return [path]


@npe2.implements.widget(
    id="some_widget", title="Create my widget", display_name="My Widget"
)
class SomeWidget:
    ...


@npe2.implements.sample_data_generator(
    id="my_plugin.generate_random_data",
    title="Generate uniform random data",
    key="random_data",
    display_name="Some Random Data (512 x 512)",
)
def random_data():
    import numpy as np

    return [(np.random.rand(10, 10))]


@impls.widget(
    id="some_function_widget",
    title="Create widget from my function",
    display_name="A Widget From a Function",
)
def make_widget_from_function(image: "napari.types.ImageData", threshold: int):
    ...
