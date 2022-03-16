import inspect
import os
from importlib import metadata

import pytest

from npe2._from_npe1 import _python_name, iter_hookimpls
from npe2.manifest.utils import SHIM_NAME_PREFIX, import_python_name

PLUGIN = os.getenv("TEST_PACKAGE_NAME")
if not PLUGIN:
    pytest.skip("skipping plugin specific tests", allow_module_level=True)


def test_entry_points():
    assert PLUGIN
    d = metadata.distribution(str(PLUGIN))
    eps = [
        ep for ep in d.entry_points if ep.group in ("napari.plugin", "napari.manifest")
    ]
    assert eps
    for ep in eps:
        module = ep.load()
        impls = list(iter_hookimpls(module))
        assert impls, f"no hookimpls in {PLUGIN}"
        for impl in impls:
            # if it takes parameters, it's not a python-name returning hook
            if inspect.signature(impl.function).parameters:
                continue
            result = impl.function()
            assert result
            if isinstance(result, dict):
                result = result.values()
            elif not isinstance(result, list):
                result = [result]
            for idx, obj in enumerate(result):
                py_name = _python_name(obj, impl.function, shim_idx=idx)
                assert import_python_name(py_name)
                assert SHIM_NAME_PREFIX not in py_name  # temporary
