from npe2 import PluginContext


def activate(context: PluginContext):
    @context.register_command("my_plugin.hello_world")
    def _hello():
        ...

    context.register_command("my_plugin.another_command", lambda: print("yo!"))


def get_reader(path: str):
    if path.endswith(".fzzy"):

        def read(path):
            return [(None,)]

        return read
