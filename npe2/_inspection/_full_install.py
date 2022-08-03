"""This module is mostly superceded by the static NPE1ModuleVisitor pattern.

It is left here for reference, but could be removed in the future.
"""
from __future__ import annotations

import site
import sys
import warnings
from contextlib import contextmanager
from importlib import metadata
from logging import getLogger
from typing import TYPE_CHECKING, Iterator, Optional

from build.env import IsolatedEnv, IsolatedEnvBuilder

if TYPE_CHECKING:
    from npe2.manifest import PluginManifest

logger = getLogger(__name__)
__all__ = [
    "fetch_manifest_with_full_install",
    "isolated_plugin_env",
]

NPE1_ENTRY_POINT = "napari.plugin"
NPE2_ENTRY_POINT = "napari.manifest"


@contextmanager
def isolated_plugin_env(
    package: str,
    version: Optional[str] = None,
    validate_npe1_imports: bool = True,
    install_napari_if_necessary: bool = True,
) -> Iterator[IsolatedEnv]:
    """Isolated env context with a plugin installed.

    The site-packages folder of the env is added to sys.path within the context.

    Parameters
    ----------
    package : str
        package name
    version : Optional[str]
        package version, by default, latest version.
    validate_npe1_imports: bool
        Whether to try to import an npe1 plugin's entry points. by default True.
    install_napari_if_necessary: bool
        If `validate_npe1_imports` is True, whether to install napari if the import
        fails.  (It's not uncommon for plugins to fail to specify napari as a
        dependency.  Othertimes, they simply need a qt backend.).  by default True.

    Yields
    ------
    build.env.IsolatedEnv
        env object that has an `install` method.
    """
    with IsolatedEnvBuilder() as env:
        # install the package
        pkg = f"{package}=={version}" if version else package
        logger.debug(f"installing {pkg} into virtual env")
        env.install([pkg])

        # temporarily add env site packages to path
        prefixes = [getattr(env, "path")]  # noqa
        if not (site_pkgs := site.getsitepackages(prefixes=prefixes)):
            raise ValueError("No site-packages found")  # pragma: no cover
        sys.path.insert(0, site_pkgs[0])
        try:
            if validate_npe1_imports:
                # try to import the plugin's entry points
                dist = metadata.distribution(package)
                ep_groups = {ep.group for ep in dist.entry_points}
                if NPE1_ENTRY_POINT in ep_groups and NPE2_ENTRY_POINT not in ep_groups:
                    try:
                        _get_loaded_mf_or_die(package)
                    except Exception:  # pragma: no cover
                        # if loading contributions fails, it can very often be fixed
                        # by installing `napari[all]` into the environment
                        if install_napari_if_necessary:
                            env.install(["napari[all]"])
                            # force reloading of qtpy
                            sys.modules.pop("qtpy", None)
                            _get_loaded_mf_or_die(package)
                        else:
                            raise
            yield env
        finally:
            # cleanup sys.path
            sys.path.pop(0)


def _get_loaded_mf_or_die(package: str) -> PluginManifest:
    """Return a fully loaded (if npe1) manifest, or raise an exception."""
    from npe2 import PluginManifest
    from npe2.manifest._npe1_adapter import NPE1Adapter

    mf = PluginManifest.from_distribution(package)
    if isinstance(mf, NPE1Adapter):
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="Error importing contributions")
            warnings.filterwarnings("error", message="Failed to convert")
            warnings.filterwarnings("ignore", message="Found a multi-layer writer")
            mf._load_contributions(save=False)
    return mf


def fetch_manifest_with_full_install(
    package: str, version: Optional[str] = None
) -> PluginManifest:
    """Fetch manifest for plugin by installing into an isolated environment."""
    # create an isolated env in which to install npe1 plugin
    with isolated_plugin_env(
        package, version, validate_npe1_imports=True, install_napari_if_necessary=True
    ):
        return _get_loaded_mf_or_die(package)
