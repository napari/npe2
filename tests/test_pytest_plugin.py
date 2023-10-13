import pytest

pytest_plugins = "pytester"

CASE1 = """
from npe2._pytest_plugin import TestPluginManager
from npe2 import PluginManager

def test_something_1(npe2pm):
    assert isinstance(npe2pm, TestPluginManager)
    assert PluginManager.instance() is npe2pm
"""

CASE2 = """
import pytest

def test_something_2(npe2pm, caplog):
    npe2pm.discover()
    assert "TestPluginManager refusing to discover plugins" in caplog.text
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
"""

CASE3 = """
from npe2 import DynamicPlugin

def test_something_3(npe2pm):
    with npe2pm.tmp_plugin(name='some_name') as plugin:
        assert isinstance(plugin, DynamicPlugin)
        assert plugin.name in npe2pm._manifests
"""

CASE4 = """
from npe2 import PluginManifest

def test_something_4(npe2pm):
    mf = PluginManifest(name='some_name')
    with npe2pm.tmp_plugin(manifest=mf) as plugin:
        assert plugin.name in npe2pm._manifests
        assert plugin.manifest is mf
"""

CASE5 = """
import pytest
from importlib.metadata import PackageNotFoundError

def test_something_5(npe2pm):
    with pytest.raises(PackageNotFoundError):
        npe2pm.tmp_plugin(package='somepackage')
"""

CASE6 = """
import pytest

def test_something_6(npe2pm):
    with pytest.raises(FileNotFoundError):
        npe2pm.tmp_plugin(manifest='some_path.yaml')
"""


@pytest.mark.parametrize("case", [CASE1, CASE2, CASE3, CASE4, CASE5, CASE6])
def test_npe2pm_fixture(pytester_pretty: pytest.Pytester, case):
    """Make sure that the npe2pm fixture works."""

    # create a temporary pytest test file
    pytester_pretty.makepyfile(case)
    pytester_pretty.runpytest().assert_outcomes(passed=1)
