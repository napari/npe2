import sys
from pathlib import Path

from .schema import PluginManifest

path = Path(sys.argv[1])
pyproj = path / "pyproject.toml"

pm = PluginManifest.from_pyproject(pyproj)

if 'json' in sys.argv:
    from pprint import pprint
    pprint(pm.dict(exclude_unset=True), indent=2)
else:
    print(pm.toml())
