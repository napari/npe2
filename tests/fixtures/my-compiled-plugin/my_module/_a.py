# mypy: disable-error-code=empty-body
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

# alternative pattern that does not require npe2 at runtime
if TYPE_CHECKING:
    from npe2 import implements
else:
    # create no-op `implements.anything(**kwargs)` decorator
    D = type("D", (), {"__getattr__": lambda *_: (lambda **_: (lambda f: f))})
    implements = D()


@implements.on_activate
def activate(ctx):
    ...


@implements.on_deactivate
def deactivate(ctx):
    ...


@implements.reader(
    id="some_reader",
    title="Some Reader",
    filename_patterns=["*.fzy", "*.fzzy"],
    accepts_directories=True,
)
def get_reader(path: str):
    ...


@implements.writer(
    id="my_writer",
    title="My Multi-layer Writer",
    filename_extensions=["*.tif", "*.tiff"],
    layer_types=["image{2,4}", "tracks?"],
)
@implements.writer(
    id="my_writer",
    title="My Multi-layer Writer",
    filename_extensions=["*.pcd", "*.e57"],
    layer_types=["points{1}", "surface+"],
)
def writer_function(path: str, layer_data: List[Tuple[Any, Dict, str]]) -> List[str]:
    ...
