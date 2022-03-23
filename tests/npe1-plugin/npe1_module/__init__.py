from functools import partial

import numpy as np
from magicgui import magic_factory
from napari_plugin_engine import napari_hook_implementation


class MyWidget:
    ...


def some_function(x: int):
    ...


def gen_data():
    ...


@napari_hook_implementation
def napari_get_reader(path):
    ...


@napari_hook_implementation
def napari_write_image(path, data, meta):
    ...


@napari_hook_implementation
def napari_write_labels(path, data, meta):
    ...


@napari_hook_implementation
def napari_provide_sample_data():
    return {
        "random data": gen_data,
        "local data": partial(np.ones, (4, 4)),
        "random image": "https://picsum.photos/1024",
        "sample_key": {
            "display_name": "Some Random Data (512 x 512)",
            "data": gen_data,
        },
        "local_ones": {
            "display_name": "Some local ones",
            "data": partial(np.ones, (4, 4)),
        },
    }


@napari_hook_implementation
def napari_experimental_provide_theme():
    return {
        "super_dark": {
            "name": "super_dark",
            "background": "rgb(12, 12, 12)",
            "foreground": "rgb(65, 72, 81)",
            "primary": "rgb(90, 98, 108)",
            "secondary": "rgb(134, 142, 147)",
            "highlight": "rgb(106, 115, 128)",
            "text": "rgb(240, 241, 242)",
            "icon": "rgb(209, 210, 212)",
            "warning": "rgb(153, 18, 31)",
            "current": "rgb(0, 122, 204)",
            "syntax_style": "native",
            "console": "rgb(0, 0, 0)",
            "canvas": "black",
        },
        "pretty_light": {
            "background": "rgb(192, 223, 139)",
        },
    }


factory = magic_factory(some_function)


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    @magic_factory
    def local_widget(y: str):
        ...

    return [
        MyWidget,
        (factory, {"name": "My Other Widget"}),
        (local_widget, {"name": "Local Widget"}),
    ]


@napari_hook_implementation
def napari_experimental_provide_function():
    def local_function(x: int):
        ...

    return [some_function, local_function]
