from npe2.manifest import PluginManifest


def create_manifest(plugin_name: str) -> str:
    """function that takes plugin name and exports manifest"""

    from napari.plugins import plugin_manager as plugin_manager

    plugin_manager.discover()

    if plugin_name not in plugin_manager.plugins:
        raise ValueError("Could not find plugin", plugin_name)

    module = plugin_manager.plugins[plugin_name]
    standard_meta = plugin_manager.get_standard_metadata(plugin_name)
    package = standard_meta["package"].replace("-", "_")

    commands = []
    for caller in plugin_manager._plugin2hookcallers[module]:
        for impl in caller.get_hookimpls():
            if impl.plugin_name != plugin_name:
                continue
            name = impl.specname.replace("napari_", "")
            id = f"{package}.{name}"
            python_name = f"{impl.function.__module__}:{impl.function.__qualname__}"
            title = " ".join(name.split("_")).title()
            commands.append({"id": id, "python_name": python_name, "title": title})

    pm = PluginManifest(
        name=package,
        publisher=standard_meta["author"],
        description=standard_meta["summary"],
        version=standard_meta["version"],
        contributions={"commands": commands},
    )
    return pm.yaml()
