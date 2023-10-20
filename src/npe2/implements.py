import contextlib
from inspect import Parameter, Signature
from typing import Any, Callable, List, Sequence, Type, TypeVar

from npe2._pydantic_compat import BaseModel

from .manifest import contributions

__all__ = [
    "CHECK_ARGS_PARAM",
    "on_activate",
    "on_deactivate",
    "reader",
    "sample_data_generator",
    "widget",
    "writer",
]


T = TypeVar("T", bound=Callable[..., Any])

CHECK_ARGS_PARAM = "ensure_args_valid"


def _build_decorator(contrib: Type[BaseModel]) -> Callable:
    """Create a decorator (e.g. `@implements.reader`) to mark an object as a contrib.

    Parameters
    ----------
    contrib : Type[BaseModel]
        The type of contribution this object implements.
    """
    # build a signature based on the fields in this contribution type, mixed with
    # the fields in the CommandContribution
    contribs: Sequence[Type[BaseModel]] = (contributions.CommandContribution, contrib)
    params: List[Parameter] = []
    for contrib in contribs:
        # iterate over the fields in the contribution types
        for field in contrib.__fields__.values():
            # we don't need python_name (since that will be gleaned from the function
            # we're decorating) ... and we don't need `command`, since that will just
            # be a string pointing to the contributions.commands entry that we are
            # creating here.
            if field.name not in {"python_name", "command"}:
                # ensure that required fields raise a TypeError if they are not provided
                default = Parameter.empty if field.required else field.get_default()
                # create the parameter and add it to the signature.
                param = Parameter(
                    field.name,
                    Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=field.outer_type_ or field.type_,
                )
                params.append(param)

    # add one more parameter to control whether the arguments in the decorator itself
    # are validated at runtime
    params.append(
        Parameter(
            CHECK_ARGS_PARAM,
            kind=Parameter.KEYWORD_ONLY,
            default=False,
            annotation=bool,
        )
    )

    signature = Signature(parameters=params, return_annotation=Callable[[T], T])

    # creates the actual `@npe2.implements.something` decorator
    # this just stores the parameters for the corresponding contribution type
    # as attributes on the function being decorated.
    def _deco(**kwargs) -> Callable[[T], T]:
        def _store_attrs(func: T) -> T:
            # If requested, assert that we've satisfied the signature when
            # the decorator is invoked at runtime.
            # TODO: improve error message to provide context
            if kwargs.pop(CHECK_ARGS_PARAM, False):
                signature.bind(**kwargs)

            # TODO: check if it's already there and assert the same id
            # store these attributes on the function
            with contextlib.suppress(AttributeError):
                setattr(func, f"_npe2_{contrib.__name__}", kwargs)

            # return the original decorated function
            return func

        return _store_attrs

    # set the signature and return the decorator
    _deco.__signature__ = signature  # type: ignore
    return _deco


# builds decorators for each of the contribution types that are essentially just
# pointers to some command.
reader = _build_decorator(contributions.ReaderContribution)
writer = _build_decorator(contributions.WriterContribution)
widget = _build_decorator(contributions.WidgetContribution)
sample_data_generator = _build_decorator(contributions.SampleDataGenerator)


def on_activate(func):
    """Mark a function to be called when a plugin is activated."""
    func.npe2_on_activate = True
    return func


def on_deactivate(func):
    """Mark a function to be called when a plugin is deactivated."""
    func.npe2_on_deactivate = True
    return func
