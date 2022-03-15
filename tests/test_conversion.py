import pytest

from npe2._from_npe1 import convert_repository, get_top_module_path, manifest_from_npe1

try:
    from importlib.metadata import PackageNotFoundError
except ImportError:
    from importlib_metadata import PackageNotFoundError  # type: ignore


@pytest.mark.filterwarnings("ignore:The distutils package is deprecated")
@pytest.mark.filterwarnings("ignore:Found a multi-layer writer, but it's not")
@pytest.mark.parametrize("package", ["svg"])
def test_conversion(package):
    assert manifest_from_npe1(package)


def test_conversion_from_module(mock_npe1_pm, npe1_plugin_module):
    mf = manifest_from_npe1(module=npe1_plugin_module)
    assert isinstance(mf.dict(), dict)


def test_conversion_from_obj_with_locals(mock_npe1_pm):
    from napari_plugin_engine import napari_hook_implementation

    class MyPlugin:
        @staticmethod
        @napari_hook_implementation
        def napari_experimental_provide_function():
            def f(x: int):
                ...

            return [f]

    with pytest.warns(UserWarning) as record:
        mf = manifest_from_npe1(module=MyPlugin)
    msg = str(record[0].message)
    assert "functions defined in local scopes are not yet supported." in msg
    assert isinstance(mf.dict(), dict)


def test_conversion_from_package(npe1_repo, mock_npe1_pm_with_plugin):
    setup_cfg = npe1_repo / "setup.cfg"
    before = setup_cfg.read_text()
    convert_repository(npe1_repo, dry_run=True)
    assert setup_cfg.read_text() == before
    assert not (npe1_repo / "npe1_module" / "napari.yaml").exists()
    convert_repository(npe1_repo, dry_run=False)
    new_setup = setup_cfg.read_text()
    assert new_setup != before
    assert (
        "[options.entry_points]\n"
        "napari.manifest = \n	npe1-plugin = npe1_module:napari.yaml"
    ) in new_setup
    assert "[options.package_data]\nnpe1_module = napari.yaml" in new_setup
    assert (npe1_repo / "npe1_module" / "napari.yaml").is_file()

    with pytest.raises(ValueError) as e:
        convert_repository(npe1_repo)
    assert "Is this package already converted?" in str(e.value)


def test_conversion_from_package_setup_py(npe1_repo, mock_npe1_pm_with_plugin):
    (npe1_repo / "setup.cfg").unlink()
    (npe1_repo / "setup.py").write_text(
        """from setuptools import setup

setup(
    name='npe1-plugin',
    entry_points={"napari.plugin": ["npe1-plugin = npe1_module"]}
)
"""
    )
    with pytest.warns(UserWarning) as record:
        convert_repository(npe1_repo)
    msg = record[0].message
    assert "Cannot auto-update setup.py, please edit setup.py as follows" in str(msg)
    assert "npe1-plugin = npe1_module:napari.yaml" in str(msg)


def test_conversion_entry_point_string(npe1_repo, mock_npe1_pm_with_plugin):
    (npe1_repo / "setup.cfg").unlink()
    (npe1_repo / "setup.py").write_text(
        """from setuptools import setup

setup(
    name='npe1-plugin',
    entry_points={"napari.plugin": "npe1-plugin = npe1_module"}
)
"""
    )
    with pytest.warns(UserWarning) as record:
        convert_repository(npe1_repo)
    msg = record[0].message
    assert "Cannot auto-update setup.py, please edit setup.py as follows" in str(msg)
    assert "npe1-plugin = npe1_module:napari.yaml" in str(msg)


def test_conversion_missing():
    with pytest.raises(ModuleNotFoundError), pytest.warns(UserWarning):
        manifest_from_npe1("does-not-exist-asdf6as987")


def test_conversion_package_is_not_a_plugin():
    with pytest.raises(PackageNotFoundError):
        manifest_from_npe1("pytest")


def test_convert_repo():
    convert_repository


def test_get_top_module_path(mock_npe1_pm_with_plugin):
    get_top_module_path("npe1-plugin")
