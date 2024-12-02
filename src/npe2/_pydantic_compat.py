try:
    # pydantic v2
    from pydantic.v1 import (
        BaseModel,
        Extra,
        Field,
        PrivateAttr,
        ValidationError,
        color,
        conlist,
        constr,
        root_validator,
        validator,
    )
    from pydantic.v1.error_wrappers import ErrorWrapper
    from pydantic.v1.fields import SHAPE_LIST
    from pydantic.v1.generics import GenericModel
    from pydantic.v1.main import ModelMetaclass
except ImportError:
    # pydantic v2
    from pydantic import (
        BaseModel,
        Extra,
        Field,
        PrivateAttr,
        ValidationError,
        color,
        conlist,
        constr,
        root_validator,
        validator,
    )
    from pydantic.error_wrappers import ErrorWrapper
    from pydantic.fields import SHAPE_LIST
    from pydantic.generics import GenericModel
    from pydantic.main import ModelMetaclass


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
    "conlist",
    "constr",
    "root_validator",
    "validator",
)
