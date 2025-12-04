from importlib.metadata import version
from types import NoneType, UnionType
from typing import get_args, get_origin

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
    ModelMetaclass = object
else:
    from pydantic import color, root_validator
    from pydantic.error_wrappers import ErrorWrapper  # type: ignore
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


def _get_root_types(type_):
    origin = get_origin(type_)
    args = get_args(type_)
    if origin is list:
        yield from _get_root_types(args[0])
    elif origin is dict:
        yield from _get_root_types(args[1])
    elif origin is UnionType:
        for arg in args:
            yield from _get_root_types(arg)
    else:
        yield type_


def _is_list_type(type_):
    if type_ is list:
        return True
    origin = get_origin(type_)
    if origin is UnionType:
        args = list(filter(lambda t: t is not NoneType, get_args(type_)))
        if len(args) == 1:
            return _is_list_type(args[0])
    return origin is list


__all__ = (
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
