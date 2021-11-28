import pytest
from magicgui import magic_factory
from napari_plugin_engine import napari_hook_implementation

from npe2._from_npe1 import manifest_from_npe1

try:
    from importlib.metadata import PackageNotFoundError
except ImportError:
    from importlib_metadata import PackageNotFoundError  # type: ignore


def gen_data():
    ...


class MyWidget:
    ...


def some_function(x: int):
    ...


some_widget = magic_factory(some_function)


class TestPlugin:
    @napari_hook_implementation
    def napari_get_reader(path):
        ...

    @napari_hook_implementation
    def napari_write_image(path, data, meta):
        ...

    @napari_hook_implementation
    def napari_write_labels(path, data, meta):
        ...

    @staticmethod
    @napari_hook_implementation
    def napari_provide_sample_data():
        return {
            "random data": gen_data,
            "random image": "https://picsum.photos/1024",
            "sample_key": {
                "display_name": "Some Random Data (512 x 512)",
                "data": gen_data,
            },
        }

    @staticmethod
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

    @staticmethod
    @napari_hook_implementation
    def napari_experimental_provide_dock_widget():
        return [MyWidget, (some_widget, {"name": "My Other Widget"})]

    @staticmethod
    @napari_hook_implementation
    def napari_experimental_provide_function():
        return some_function


def test_conversion():
    with pytest.warns(UserWarning):
        assert manifest_from_npe1("svg")


def test_conversion2():
    mf = manifest_from_npe1(module=TestPlugin)
    assert isinstance(mf.dict(), dict)


def test_conversion_missing():
    with pytest.raises(ModuleNotFoundError), pytest.warns(UserWarning):
        manifest_from_npe1("does-not-exist-asdf6as987")


def test_conversion_package_is_not_a_plugin():
    with pytest.raises(PackageNotFoundError):
        manifest_from_npe1("pytest")
