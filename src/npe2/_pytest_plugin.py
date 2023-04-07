import logging
import warnings
from typing import Optional, Union
from unittest.mock import patch

import pytest

from npe2 import DynamicPlugin, PluginManager, PluginManifest

logger = logging.getLogger(__name__)


class TestPluginManager(PluginManager):
    """A PluginManager subclass suitable for use in testing."""

    def discover(self, *_, **__) -> int:
        """Discovery is blocked in the TestPluginManager."""
        logger.warning(
            "NOTE: TestPluginManager refusing to discover plugins. "
            "You may add plugins to this test plugin manager using `tmp_plugin()`."
        )
        return 0

    def tmp_plugin(
        self,
        manifest: Optional[Union[PluginManifest, str]] = None,
        package: Optional[str] = None,
        name: Optional[str] = None,
    ) -> DynamicPlugin:
        """Create a DynamicPlugin instance using this plugin manager.

        If providing arguments, provide only one of 'manifest', 'package', 'name'.

        Parameters
        ----------
        manifest : Union[PluginManifest, str]
            A manifest to use for this plugin. If a string, it is assumed to be the
            path to a manifest file (which must exist), otherwise must be a
            PluginManifest instance.
        package : str
            Name of an installed plugin/package.
        name : str
            If neither `manifest` or `package` is provided, a new DynamicPlugin is
            created with this name, by default "tmp_plugin"

        Returns
        -------
        DynamicPlugin
            be sure to enter the DynamicPlugin context to register the plugin.

        Examples
        --------
        >>> def test_something_with_only_my_plugin_registered(npe2pm):
        ...    with npe2pm.tmp_plugin(package='my-plugin') as plugin:
        ...        ...

        >>> def test_something_with_specific_manifest_file_registered(npe2pm):
        ...    mf_file = Path(__file__).parent / 'my_manifest.yaml'
        ...    with npe2pm.tmp_plugin(manifest=str(mf_file)) as plugin:
        ...        ...
        """
        if manifest is not None:
            if package or name:  # pragma: no cover
                warnings.warn(
                    "`manifest` overrides the `package` and `name` arguments. "
                    "Please provide only one.",
                    stacklevel=2,
                )
            if isinstance(manifest, PluginManifest):
                mf = manifest
            else:
                mf = PluginManifest.from_file(manifest)
        elif package:
            if name:  # pragma: no cover
                warnings.warn(
                    "`package` overrides the `name` argument. Please provide only one.",
                    stacklevel=2,
                )
            mf = PluginManifest.from_distribution(package)
        else:
            name = name or "tmp_plugin"
            i = 0
            while name in self._manifests:  # pragma: no cover
                # guarantee that name is unique
                name = f"{name}_{i}"
                i += 1
            mf = PluginManifest(name=name)
        return DynamicPlugin(mf.name, plugin_manager=self, manifest=mf)


@pytest.fixture
def npe2pm():
    """Return mocked Global plugin manager instance, unable to discover plugins.

    Examples
    --------
    >>> @pytest.fixture(autouse=True)
    ... def mock_npe2_pm(npe2pm):
    ...     # Auto-use this fixture to prevent plugin discovery.
    ...     return npe2pm
    """
    _pm = TestPluginManager()
    with patch("npe2.PluginManager.instance", return_value=_pm):
        yield _pm
