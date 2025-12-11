from types import NoneType, UnionType
from typing import Annotated, Dict, List, Union, get_args, get_origin  # noqa

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    ValidationError,
    conlist,
    constr,
    model_validator,
    validator,
)
from pydantic_extra_types import color

GenericModel = BaseModel

ModelMetaclass = object


# TODO: do we enforce uniqueness for conlist? This was the case in all our uses,
#       but pydantic now encourages using sets for that... however everthyng breaks
#       in weird ways when I switch to sets. So maybe for a later time...


def _iter_inner_types(type_):
    origin = get_origin(type_)
    args = get_args(type_)
    if origin in (list, List):  # noqa
        yield from _iter_inner_types(args[0])
    elif origin in (dict, Dict):  # noqa
        yield from _iter_inner_types(args[1])
    if origin is Annotated:
        yield from _iter_inner_types(args[0])
    elif origin in (UnionType, Union):
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
    if origin in (UnionType, Union):
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
