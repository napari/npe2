try:
    # pydantic v2
    from pydantic.v1 import BaseModel, Extra, Field, ValidationError, root_validator, validator, PrivateAttr, color, conlist
    from pydantic.v1.main import ModelMetaclass
    from pydantic.v1.error_wrappers import ErrorWrapper
    from pydantic.v1.generics import GenericModel
    from pydantic.v1.fields import SHAPE_LIST
except ImportError:
    # pydantic v2
    from pydantic import BaseModel, Extra, Field, ValidationError, root_validator, validator, PrivateAttr, color, conlist
    from pydantic.main import ModelMetaclass
    from pydantic.error_wrappers import ErrorWrapper
    from pydantic.generics import GenericModel
    from pydantic.fields import SHAPE_LIST


__all__ = (
    'BaseModel',
    'Extra',
    'Field',
    'ValidationError',
    'root_validator',
    'validator',
    'PrivateAttr',
    'color',
    'conlist',
    'ModelMetaclass',
    'ErrorWrapper',
    'GenericModel',
    'SHAPE_LIST'
)