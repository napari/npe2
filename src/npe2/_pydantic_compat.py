from importlib.metadata import version
from types import NoneType, UnionType
from typing import Union, get_args, get_origin

from packaging.version import parse
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    ValidationError,
    conlist,
    constr,
    validator,
)

if parse(version("pydantic")) > parse("2"):
    from pydantic import model_validator
    from pydantic_extra_types import color

    GenericModel = BaseModel

    ModelMetaclass = object
else:
    from pydantic import color, root_validator
    from pydantic.generics import GenericModel  # type: ignore
    from pydantic.main import ModelMetaclass  # type: ignore

    # doing just minimal changes to support our uses
    old_constr = constr

    def constr(*args, pattern=None, **kwargs):
        return old_constr(*args, regex=pattern, **kwargs)

    old_conlist = conlist

    def conlist(*args, min_length=None, **kwargs):
        return old_conlist(*args, min_items=min_length, **kwargs)

    def model_validator(*, mode):
        pre = mode in ("before", "wrap")
        return root_validator(pre=pre)


# TODO: do we enforce uniqueness for conlist? This was the case in all our uses,
#       but pydantic now encourages using sets for that... however everthyng breaks
#       in weird ways when I switch to sets. So maybe for a later time...


def _iter_inner_types(type_):
    origin = get_origin(type_)
    args = get_args(type_)
    if origin is list:
        yield from _iter_inner_types(args[0])
    elif origin is dict:
        yield from _iter_inner_types(args[1])
    elif origin is UnionType:
        for arg in args:
            yield from _iter_inner_types(arg)
    elif type_ is not NoneType:
        yield type_


def _get_inner_type(type_):
    """Roughly replacing pydantic.v1 Field.type_"""
    return Union[tuple(_iter_inner_types(type_))]  # noqa


def _get_outer_type(type_):
    """Roughly replacing pydantic.v1 Field.outer_type_"""
    origin = get_origin(type_)
    args = get_args(type_)
    if origin is UnionType:
        # filter args to remove optional None
        args = tuple(filter(lambda t: t is not NoneType, get_args(type_)))
        if len(args) == 1:
            # it was just optional, pretend there was no None
            return _get_outer_type(args[0])
        # It's an actual union of types, so there's no "outer type"
        return None
    if origin is not None:
        return origin
    return type_


def _is_list_type(type_):
    """Roughly replacing pydantic.v1 comparison to SHAPE_LIST"""
    return _get_outer_type(type_) is list


__all__ = (
    "BaseModel",
    "Field",
    "GenericModel",
    "ModelMetaclass",
    "PrivateAttr",
    "ValidationError",
    "color",
    "conlist",
    "constr",
    "model_validator",
    "validator",
)
