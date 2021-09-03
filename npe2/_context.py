"""
just exploring for a moment...
this is an ugly straight conversion of the javascript code.
"""

from __future__ import annotations

import sys
from enum import IntEnum, auto
from typing import Any, Generic, NamedTuple, Protocol, TypeVar

STATIC_VALUES: dict[str, Any] = {
    "is_linux": sys.platform.startswith("linux"),
    "is_mac": sys.platform == "darwin",
    "is_windows": sys.platform.startswith("win32"),
}


class ContextKeyExprType(IntEnum):
    FALSE = auto()
    TRUE = auto()
    DEFINED = auto()
    NOT = auto()
    EQUALS = auto()
    NOT_EQUALS = auto()
    AND = auto()
    REGEX = auto()
    NOT_REGEX = auto()
    OR = auto()
    IN = auto()
    NOT_IN = auto()
    GREATER = auto()
    GREATER_EQUALS = auto()
    SMALLER = auto()
    SMALLER_EQUALS = auto()


# ContextKeyExpression = Union[
#     ContextKeyFalseExpr,
#     ContextKeyTrueExpr,
#     ContextKeyDefinedExpr,
#     ContextKeyNotExpr,
#     ContextKeyEqualsExpr,
#     ContextKeyNotEqualsExpr,
#     ContextKeyRegexExpr,
#     ContextKeyNotRegexExpr,
#     ContextKeyAndExpr,
#     ContextKeyOrExpr,
#     ContextKeyInExpr,
#     ContextKeyNotInExpr,
#     ContextKeyGreaterExpr,
#     ContextKeyGreaterEqualsExpr,
#     ContextKeySmallerExpr,
#     ContextKeySmallerEqualsExpr,
# ]


# fmt: off
class PContextKeyDefinedExpr(Protocol):
    def cmp(self, other) -> float: ...
    def equals(self, other) -> bool: ...
    def evaluate(self, context) -> bool: ...
    def serialize(self, ) -> str: ...
    def keys(self, ) -> list[str]: ...
    # def map(self, mapFnc) -> 'ContextKeyExpression': ...
    # def negate(self, ) -> 'ContextKeyExpression': ...
# fmt: on


class ContextKeyExpression:
    key: str
    keys: list[str]
    type_: ContextKeyExprType

    def __init__(self, key: str, negated: ContextKeyExpression | None = None):
        self.key = key
        self.negated = negated

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ContextKeyExpression):
            return NotImplemented
        if o.type_ == self.type_:
            return self.key == o.key
        return False

    def __invert__(self) -> ContextKeyExpression:
        # negate
        ...

    def __str__(self) -> str:
        # serialize
        return self.key

    def evaluate(self, ctx) -> bool:
        ...


class ContextKeyInfo(NamedTuple):
    key: str
    type: type | None
    description: str | None


T = TypeVar("T")


class RawContextKey(Generic[T]):
    _info: list[ContextKeyInfo] = []

    def __init__(
        self,
        key: str,
        default_value: T | None = None,
        description: str | None = None,
        *,
        hide: bool = False,
    ) -> None:
        self.key = key
        self._default_value = default_value
        if not hide:
            type_ = type(default_value) if default_value is not None else None
            self._info.append(ContextKeyInfo(key, type_, description))

    @classmethod
    def all(cls) -> list[ContextKeyInfo]:
        return list(cls._info)

    def bind_to(self, target: AbstractContextKeyService) -> ContextKey[T]:
        return target.create_key(self.key, self._default_value)


class ContextKey(Generic[T]):
    def __init__(
        self, service: AbstractContextKeyService, key: str, default_value: T | None
    ) -> None:
        self._service = service
        self._key = key
        self._default_value = default_value
        self.reset()

    def get(self) -> T | None:
        return self._service.get_context_key_value(self._key)

    def set(self, value: T) -> None:
        self._service.set_context(self._key, value)

    def reset(self) -> None:
        if self._default_value is None:
            self._service.remove_context(self._key)
        else:
            self._service.set_context(self._key, self._default_value)


class NullContext(Context):
    __instance: NullContext | None = None

    def __init__(self) -> None:
        super().__init__(-1, None)

    @classmethod
    def instance(cls) -> NullContext:
        if cls.__instance is None:
            cls.__instance = NullContext()
        return cls.__instance
