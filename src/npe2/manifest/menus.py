import warnings

warnings.warn(
    "please import menus from npe2.manifest.contributions",
    DeprecationWarning,
    stacklevel=2,
)

from .contributions._menus import *  # noqa
