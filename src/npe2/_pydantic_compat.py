import sys
from importlib.metadata import version
from packaging.version import parse

from pydantic import BaseModel, Extra, Field, PrivateAttr, ValidationError, conset, constr, validator

if parse(version('pydantic')) > parse('2'):
    from pydantic_extra_types import color
    from pydantic import model_validator
    GenericModel = BaseModel

    # TODO: check these
    ErrorWrapper = ValidationError
    SHAPE_LIST = 2
    ModelMetaclass = object
else:
    from pydantic.generics import GenericModel
    from pydantic import root_validator
    from pydantic import color
    from pydantic.fields import SHAPE_LIST
    from pydantic.error_wrappers import ErrorWrapper
    from pydantic.main import ModelMetaclass

    # doing just minimal changes to support our uses
    old_constr = constr
    def constr(*args, pattern=None, **kwargs):
        return old_constr(*args, regex=pattern, **kwargs)

    old_conset = conset
    def conset(*args, min_length=None, **kwargs):
        return old_conset(*args, min_items=min_length, **kwargs)

    def model_validator(*, mode):
        pre = mode in ('before', 'wrap')
        return root_validator(pre=pre)

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
    "root_validator",
    "validator",
)
