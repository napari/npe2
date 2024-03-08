from importlib.metadata import PackageNotFoundError

import pytest

from npe2._inspection import _from_npe1
from npe2._inspection._from_npe1 import (
    convert_repository,
    get_top_module_path,
    manifest_from_npe1,
)


@pytest.mark.filterwarnings("ignore:The distutils package is deprecated")
@pytest.mark.filterwarnings("ignore:Found a multi-layer writer in")
@pytest.mark.parametrize("package", ["svg"])
def test_conversion(package):
    assert manifest_from_npe1(package)


@pytest.mark.filterwarnings("ignore:Failed to convert napari_provide_sample_data")
@pytest.mark.filterwarnings("ignore:Error converting function")
@pytest.mark.filterwarnings("ignore:Error converting dock widget")
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


@pytest.mark.filterwarnings("ignore:Failed to convert napari_provide_sample_data")
@pytest.mark.filterwarnings("ignore:Error converting function")
@pytest.mark.filterwarnings("ignore:Error converting dock widget")
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


@pytest.mark.filterwarnings("ignore:Failed to convert napari_provide_sample_data")
@pytest.mark.filterwarnings("ignore:Error converting function")
@pytest.mark.filterwarnings("ignore:Error converting dock widget")
def test_conversion_from_package_editable(npe1_repo, mock_npe1_pm_with_plugin_editable):
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


def _assert_expected_errors(record: pytest.WarningsRecorder):
    assert len(record) == 4
    msg = str(record[0].message)
    assert "Error converting dock widget [2] from 'npe1_module'" in msg
    msg = str(record[1].message)
    assert "Error converting function [1] from 'npe1_module'" in msg
    msg = str(record[2].message)
    assert "Failed to convert napari_provide_sample_data in 'npe1-plugin'" in msg
    assert "could not get resolvable python name" in msg
    msg = str(record[3].message)
    assert "Cannot auto-update setup.py, please edit setup.py as follows" in msg
    assert "npe1-plugin = npe1_module:napari.yaml" in msg


def test_conversion_from_package_setup_py(npe1_repo, mock_npe1_pm_with_plugin):
    (npe1_repo / "setup.cfg").unlink()
    (npe1_repo / "setup.py").write_text(
        """from setuptools import setup

NAME = 'npe1-plugin'
setup(
    name=NAME,
    entry_points={"napari.plugin": ["npe1-plugin = npe1_module"]}
)
"""
    )
    with pytest.warns(UserWarning) as record:
        convert_repository(npe1_repo)
    _assert_expected_errors(record)


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
    _assert_expected_errors(record)


def test_conversion_missing():
    with pytest.raises(
        PackageNotFoundError,
        match="No package or entry point found with name",
    ):
        manifest_from_npe1("does-not-exist-asdf6as987")


def test_conversion_package_is_not_a_plugin():
    with pytest.raises(
        PackageNotFoundError,
        match="No package or entry point found with name",
    ):
        manifest_from_npe1("pytest")


def test_get_top_module_path(mock_npe1_pm_with_plugin):
    get_top_module_path("npe1-plugin")


def test_python_name_local():
    def f():
        return lambda x: None

    with pytest.raises(ValueError) as e:
        _from_npe1._python_name(f())

    assert "functions defined in local scopes are not yet supported" in str(e.value)


def test_guess_fname_patterns():
    def get_reader1(path):
        if isinstance(path, str) and path.endswith((".tiff", ".tif")):
            return 1

    def get_reader2(path):
        if path.endswith(".xyz"):
            return 1

    assert _from_npe1._guess_fname_patterns(get_reader1) == ["*.tiff", "*.tif"]
    assert _from_npe1._guess_fname_patterns(get_reader2) == ["*.xyz"]
