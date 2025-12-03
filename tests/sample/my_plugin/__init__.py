from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from npe2 import PluginContext
from npe2.types import PathOrPaths

if TYPE_CHECKING:
    import napari.types


def activate(context: PluginContext):
    @context.register_command("my_plugin.hello_world")
    def _hello(): ...

    context.register_command("my_plugin.another_command", lambda: print("yo!"))


def deactivate(context: PluginContext):
    """just here for tests"""


def get_reader(path: PathOrPaths):
    if isinstance(path, list):

        def read(path):
            assert isinstance(path, list)
            return [(None,)]

        return read
    assert isinstance(path, str)  # please mypy.
    if path.endswith(".fzzy"):

        def read(path):
            assert isinstance(path, str)
            return [(None,)]

        return read
    else:
        raise ValueError("Test plugin should not receive unknown data")


def url_reader(path: str):
    if path.startswith("http"):

        def read(path):
            return [(None,)]

        return read


def writer_function(path: str, layer_data: list[tuple[Any, dict, str]]) -> list[str]:
    class Arg(BaseModel):
        data: Any
        meta: dict
        layer_type: str

    for e in layer_data:
        Arg(data=e[0], meta=e[1], layer_type=e[2])

    return [path]


def writer_function_single(path: str, layer_data: Any, meta: dict) -> list[str]:
    class Arg(BaseModel):
        data: Any
        meta: dict

    Arg(data=layer_data, meta=meta)

    return [path]


class SomeWidget: ...


def random_data():
    import numpy as np

    return [np.random.rand(10, 10)]


def make_widget_from_function(image: "napari.types.ImageData", threshold: int): ...
