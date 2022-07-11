from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from npe2 import implements
else:
    D = type("D", (), {"__getattr__": lambda *_: (lambda **_: (lambda f: f))})
    implements = D()


@implements.widget(id="some_widget", title="Create my widget", display_name="My Widget")
class SomeWidget:
    ...


@implements.sample_data_generator(
    id="my-plugin.generate_random_data",  # the plugin-name is optional
    title="Generate uniform random data",
    key="random_data",
    display_name="Some Random Data (512 x 512)",
)
def random_data():
    ...


@implements.widget(
    id="some_function_widget",
    title="Create widget from my function",
    display_name="A Widget From a Function",
    autogenerate=True,
)
def make_widget_from_function(x: int, threshold: int):
    ...
