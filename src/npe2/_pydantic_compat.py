from importlib.metadata import version
from typing import Union, get_args, get_origin

from packaging.version import parse
from pydantic import (
    BaseModel,
    Extra,
    Field,
    PrivateAttr,
    ValidationError,
    conset,
    constr,
    validator,
)

if parse(version("pydantic")) > parse("2"):
    from pydantic import model_validator
    from pydantic_extra_types import color

    GenericModel = BaseModel

    # TODO: check these
    ErrorWrapper = ValidationError
    SHAPE_LIST = 2
    ModelMetaclass = object
else:
    from pydantic import color, root_validator
    from pydantic.error_wrappers import ErrorWrapper  # type: ignore
    from pydantic.fields import SHAPE_LIST  # type: ignore
    from pydantic.generics import GenericModel  # type: ignore
    from pydantic.main import ModelMetaclass  # type: ignore

    # doing just minimal changes to support our uses
    old_constr = constr

    def constr(*args, pattern=None, **kwargs):
        return old_constr(*args, regex=pattern, **kwargs)

    old_conset = conset

    def conset(*args, min_length=None, **kwargs):
        return old_conset(*args, min_items=min_length, **kwargs)

    def model_validator(*, mode):
        pre = mode in ("before", "wrap")
        return root_validator(pre=pre)


def get_root_types(type_):
    origin = get_origin(type_)
    args = get_args(type_)
    if origin in (list, list):
        yield from get_root_types(args[0])
    elif origin in (dict, dict):
        yield from get_root_types(args[1])
    elif origin == Union:
        for arg in args:
            yield from get_root_types(arg)
    else:
        yield type_


__all__ = (
    "SHAPE_LIST",
    "BaseModel",
    "ErrorWrapper",
    "Extra",
    "Field",
    "GenericModel",
    "ModelMetaclass",
    "PrivateAttr",
    "ValidationError",
    "color",
    "conset",
    "constr",
    "model_validator",
    "validator",
)
