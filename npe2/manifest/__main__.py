import sys
from pathlib import Path

from .schema import PluginManifest

path = Path(sys.argv[1])
pyproj = path / "pyproject.toml"

pm = PluginManifest.from_pyproject(pyproj)

if 'json' in sys.argv:
    print(pm.json(exclude_unset=True))
elif 'yaml' in sys.argv:
    print(pm.yaml())
else:
    print(pm.toml())
