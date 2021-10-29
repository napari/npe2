from napari_plugin_engine import PluginManager

from . import hook_specifications

plugin_manager = PluginManager("napari")
with plugin_manager.discovery_blocked():
    plugin_manager.add_hookspecs(hook_specifications)
plugin_manager.discover()
