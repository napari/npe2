import warnings

warnings.warn(
    "Please import PackageMetadata from 'npe2' or from 'npe2.manifest'",
    DeprecationWarning,
    stacklevel=2,
)

from ._package_metadata import *  # noqa
