from enum import Enum
from typing import List, Tuple

from npe2._pydantic_compat import BaseModel, Extra, Field, validator
from npe2.manifest.utils import Executable


class LayerType(str, Enum):
    graph = "graph"
    image = "image"
    labels = "labels"
    points = "points"
    shapes = "shapes"
    surface = "surface"
    tracks = "tracks"
    vectors = "vectors"


class LayerTypeConstraint(BaseModel):
    """Layer type constraints.

    A writer plugin can declare that it will write 0 or more layers of a
    specific type.

    For example:

    ```
        image      Write exactly 1 image layer.
        image?     Write 0 or 1 image layes.
        image+     Write 1 or more image layers.
        image*     Write 0 or more image layers.
        image{k}   Write exactly k image layres.
        image{m,n} Write between m and n layers (inclusive range). Must have m<=n.
    ```

    When a type is not present in the list of constraints, that
    corresponds to a writer that is not compatible with that type.

    For example, a writer declaring:

    ```
        layer_types=["image+", "points*"]
    ```

    would not be selected when trying to write an `image` and a `vector`
    layer because the above only works for cases with 0 `vector` layers.

    Note that just because a writer declares compatibility with a layer
    type does not mean it actually writes that type.  In the example
    above, the writer might accept a set of layers containing `image`s and
    `point`s, but the write command might just ignore the `point` layers
    """

    layer_type: LayerType
    bounds: Tuple[int, int] = Field(
        ...,
        description="This writer consumes between bounds[0] and bounds[1] "
        "layers of `layer_type`",
    )

    @validator("bounds")
    def check_bounds(cls, v):
        mn, mx = v
        assert mn >= 0, "min must be >= 0"
        assert mx > mn, "max must be > min"
        return v

    @classmethod
    def zero(cls, layer_type: LayerType) -> "LayerTypeConstraint":
        return cls(layer_type=layer_type, bounds=(0, 1))

    def is_zero(self) -> bool:
        return self.bounds == (0, 1)

    def max(self) -> int:
        return max(0, self.bounds[1] - 1)

    @classmethod
    def from_str(cls, expr: str) -> "LayerTypeConstraint":
        """Parse layer-type constraint expressions.

        These have the form '<layer_type><range>' where <range> is one of:
        '?', '+', '*', '{k}', '{m,n}'.

        '?' means 0 or 1.
        '+' means 1 or more.
        '*' means 0 or more.
        '{k}' means exactly k.
        '{m,n}' means between m and n (inclusive).
        """
        # Writers won't accept more than this number of layers.
        MAX_LAYERS = 1 << 32

        def parse(expr):
            if expr.endswith("?"):
                return (0, 2), LayerType(expr[:-1])
            elif expr.endswith("+"):
                return (1, MAX_LAYERS), LayerType(expr[:-1])
            elif expr.endswith("*"):
                return (0, MAX_LAYERS), LayerType(expr[:-1])
            elif expr.endswith("}"):
                rest, _, range_expr = expr[:-1].rpartition("{")
                if "," in range_expr:
                    m, n = range_expr.split(",")
                    return (int(m), int(n) + 1), LayerType(rest)
                else:
                    k = int(range_expr)
                    return (k, k + 1), LayerType(rest)
            else:
                return (1, 2), LayerType(expr)

        bounds, lt = parse(expr)
        return cls(layer_type=lt, bounds=bounds)


class WriterContribution(Executable[List[str]]):
    r"""Contribute a layer writer.

    Writers accept data from one or more layers and write them to file. Writers declare
    support for writing one or more **layer_types**, may be associated with specific
    **filename_patterns** (e.g. "\*.tif", "\*.zip") and are invoked whenever
    `viewer.layers.save('some/path.ext')` is used on the command line, or when a user
    requests to save one or more layers in the graphical user interface with `File ->
    Save Selected Layer(s)...` or `Save All Layers...`
    """

    command: str = Field(
        ..., description="Identifier of the command providing a writer."
    )
    layer_types: List[str] = Field(
        ...,
        description="List of layer type constraints. These determine what "
        "layers (or combinations thereof) this writer handles.",
    )
    # An empty filename_extensions list matches any file extension. Making the
    # default something like ['.*'] is tempting but we don't actually use
    # these for glob matching and supporting this default ends up making the
    # code more complicated.
    filename_extensions: List[str] = Field(
        default_factory=list,
        description="List of filename extensions compatible with this writer. "
        "The first entry is used as the default if necessary. Empty by default. "
        "When empty, any filename extension is accepted.",
    )
    display_name: str = Field(
        default="",
        description="Brief text used to describe this writer when presented. "
        "Empty by default. When present, this string is presented in the save dialog "
        "along side the plugin name and may be used to distinguish the kind of "
        "writer for the user. E.g. “lossy” or “lossless”.",
    )

    def layer_type_constraints(self) -> List[LayerTypeConstraint]:
        spec = [LayerTypeConstraint.from_str(lt) for lt in self.layer_types]
        unspecified_types = set(LayerType) - {lt.layer_type for lt in spec}
        return spec + [LayerTypeConstraint.zero(lt) for lt in unspecified_types]

    def __hash__(self):
        return hash(
            (
                self.command,
                str(self.layer_types),
                str(self.filename_extensions),
                self.display_name,
            )
        )

    class Config:
        extra = Extra.forbid

    @validator("layer_types")
    def _parsable_layer_type_expr(cls, layer_types: List[str]) -> List[str]:
        try:
            # a successful parse means the string is valid
            for lt in layer_types:
                LayerTypeConstraint.from_str(lt)
        except Exception as e:
            raise ValueError(f"Could not parse layer_types: {layer_types}. {e}") from e
        return layer_types

    @validator("layer_types")
    def _nonempty_layer_types(cls, layer_types: List[str]) -> List[str]:
        """If layer_types is empty, raise a ValueError."""
        if not layer_types:
            raise ValueError("layer_types must not be empty")
        return layer_types

    @validator("layer_types")
    def _layer_types_unique(cls, layer_types: List[str]) -> List[str]:
        """Each layer type can be refered to at most once."""
        from collections import Counter

        c = Counter(LayerTypeConstraint.from_str(lt).layer_type for lt in layer_types)
        if any(c[lt] > 1 for lt in c):
            raise ValueError(f"Duplicate layer type in {layer_types}")
        return layer_types

    @validator("filename_extensions")
    def _coerce_common_glob_patterns(cls, exts: List[str]) -> List[str]:
        """If any of the listed extensions are common glob patterns, replace the
        list with one of all extensions.

        Coercions:
        1. File extensions beginning with '*' have their leading '*' removed.
        2. File extensions lacking a leading '.' have a leading '.' added.

        Rules:
        3. File extensions must start with '.' or '*.'
        4. File extensions must be at least two characters long.
        """

        exts = [f".{e.lstrip('*.')}" for e in exts]

        if any(len(e) < 2 for e in exts):
            raise ValueError(
                "Invalid file extension: Must have one character past the '.'"
            )
        return exts
