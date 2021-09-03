import sys

from npe2 import PluginManifest

pm = list(PluginManifest.discover())[0]

if "json" in sys.argv:
    print(pm.json(exclude_unset=True))
elif "yaml" in sys.argv:
    print(pm.yaml())
else:
    print(pm.toml())
