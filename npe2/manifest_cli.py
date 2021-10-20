from napari.plugins._plugin_manager import NapariPluginManager

from npe2.manifest import PluginManifest


def create_manifest(plugin_name: str, plugin_manager: None) -> str:
    """function that takes plugin name and exports manifest"""

    if plugin_manager is None:
        plugin_manager = NapariPluginManager()

    for current_name, plugin in sorted(
        plugin_manager.plugins.items(), key=lambda x: x[0]
    ):
        if current_name == plugin_name:
            name = plugin_name
            publisher = plugin_manager.get_metadata(plugin, "author")
            display_name = plugin_manager.get_standard_metadata(plugin_name)["package"]
            description = plugin_manager.get_metadata(plugin, "summary")
            version = plugin_manager.get_metadata(plugin, "version")

            commands = []
            for hook in plugin_manager.get_standard_metadata(plugin_name)["hooks"]:
                package = plugin_manager.get_standard_metadata(plugin_name)["package"]
                plugin_manager.get_standard_metadata(plugin_name)["hooks"]
                hk = hook.split("napari_")[1]
                id = package + "." + hk
                python_name = plugin_manager.plugins[plugin_name].__name__ + ":" + hook
                title = " ".join(hook.split("_"))
                commands.append({"id": id, "python_name": python_name, "title": title})

            contributions = {"commands": commands}

            pm = PluginManifest(
                name=name,
                publisher=publisher,
                display_name=display_name,
                description=description,
                version=version,
                contributions=contributions,
            )

            return pm.yaml()

    return None
