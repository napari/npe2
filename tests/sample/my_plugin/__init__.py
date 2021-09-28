def activate(context):
    from npe2 import register_command

    @register_command("my_plugin.hello_world")
    def _hello():
        ...

    register_command("my_plugin.another_command", lambda: print("yo!"))


def get_reader(path):
    ...
