"""
just exploring for a moment...
this is an ugly straight conversion of the javascript code.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
)

import sys
from enum import IntEnum, auto
from psygnal import Signal

if TYPE_CHECKING:
    from napari.components import LayerList


STATIC_VALUES: Dict[str, Any] = {
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
	def keys(self, ) -> List[str]: ...
	# def map(self, mapFnc) -> 'ContextKeyExpression': ...
	# def negate(self, ) -> 'ContextKeyExpression': ...
# fmt: on


class ContextKeyInfo(NamedTuple):
    key: str
    type: Optional[Type]
    description: Optional[str]


T = TypeVar("T")


class RawContextKey(Generic[T]):
    _info: List[ContextKeyInfo] = []

    def __init__(
        self,
        key: str,
        default_value: Optional[T] = None,
        description: Optional[str] = None,
        *,
        hide: bool = False,
    ) -> None:
        self.key = key
        self._default_value = default_value
        if not hide:
            type_ = type(default_value) if default_value is not None else None
            self._info.append(ContextKeyInfo(key, type_, description))

    @classmethod
    def all(cls) -> List[ContextKeyInfo]:
        return list(cls._info)

    def bind_to(self, target: AbstractContextKeyService) -> ContextKey[T]:
        return target.create_key(self.key, self._default_value)


class ContextKey(Generic[T]):
    def __init__(
        self, service: AbstractContextKeyService, key: str, default_value: Optional[T]
    ) -> None:
        self._service = service
        self._key = key
        self._default_value = default_value
        self.reset()

    def get(self) -> Optional[T]:
        return self._service.get_context_key_value(self._key)

    def set(self, value: T) -> None:
        self._service.set_context(self._key, value)

    def reset(self) -> None:
        if self._default_value is None:
            self._service.remove_context(self._key)
        else:
            self._service.set_context(self._key, self._default_value)


class Context:
    def __init__(self, id: int, parent: Optional[Context] = None) -> None:
        self._id = id
        self._parent = parent
        self._value = {"_contextId": id}

    def set_value(self, key: str, value: Any) -> bool:
        if self._value.get(key) != value:
            self._value[key] = value
            return True
        return False

    def get_value(self, key: str) -> Any:
        val = self._value.get(key, "undefined")
        if val == "undefined" and self._parent:
            return self._parent.get_value(key)
        return None if val == "undefined" else val

    def remove_value(self, key: str) -> bool:
        if key in self._value:
            del self._value[key]
            return True
        return False

    def update_parent(self, parent: Context) -> None:
        self._parent = parent


class NullContext(Context):
    __instance: Optional[NullContext] = None

    def __init__(self) -> None:
        super().__init__(-1, None)

    @classmethod
    def instance(cls) -> NullContext:
        if cls.__instance is None:
            cls.__instance = NullContext()
        return cls.__instance


class AbstractContextKeyService:
    contextChanged = Signal()

    def __init__(self, id: int) -> None:
        self._is_disposed: bool = False
        self._context_id = id

    # def change_events_buffered(self): ...

    @property
    def context_id(self) -> int:
        return self._context_id

    def create_key(self, key: str, default_value: Optional[T]) -> ContextKey[T]:
        if self._is_disposed:
            raise RuntimeError(f"{type(self)} has been disposed.")
        return ContextKey(self, key, default_value)

    def set_context(self, key: str, value: Any) -> None:
        if self._is_disposed:
            return
        context = self.get_context_values_container(self._context_id)
        if not context:
            return
        if context.set_value(key, value):
            self.contextChanged.emit(key)

    def get_context_key_value(self, key: str) -> Any:
        if self._is_disposed:
            return None
        return self.get_context_values_container(self._context_id).get_value(key)

    def remove_context(self, key: str) -> None:
        if self._is_disposed:
            return
        if self.get_context_values_container(self._context_id).remove_value(key):
            self.contextChanged.emit(key)

    @abstractmethod
    def dispose(self) -> None:
        ...

    @abstractmethod
    def get_context_values_container(self, context_id: int) -> Context:
        ...


class ContextKeyService(AbstractContextKeyService):
    _contexts: Dict[int, Context]

    def __init__(self) -> None:
        super().__init__(0)
        self._to_dispose = set()
        self._last_context_id = 0
        self._contexts = {self._context_id: Context(self._context_id)}

    def dispose(self) -> None:
        self.contextChanged._slots.clear()
        self._is_disposed = True
        for item in self._to_dispose:
            item.dispose()

    def get_context_values_container(self, context_id) -> Context:
        if not self._is_disposed and (context_id in self._contexts):
            return self._contexts[context_id]
        return NullContext.instance()

    def create_child_context(self, parent_id: Optional[int] = None) -> int:
        parent_id = parent_id or self._context_id
        if self._is_disposed:
            raise RuntimeError(f"{type(self)} has been disposed.")
        self._last_context_id += 1
        id = self._last_context_id
        self._contexts[id] = Context(id, self.get_context_values_container(parent_id))
        return id


class LayerListContextKeys:
    selection_count = RawContextKey(
        "layers_selection_count",
        0,
        "Number of layers currently selected",
    )
    all_layers_linked = RawContextKey(
        "all_layers_linked",
        False,
        "True when all selected layers are linked.",
    )
    unselected_links = RawContextKey(
        "unselected_linked_layers",
        0,
        "Number of unselected layers linked to selected layer(s)",
    )
    active_is_rgb = RawContextKey(
        "active_layer_is_rgb",
        False,
        "True when the active layer is RGB",
    )
    only_images_selected = RawContextKey(
        "only_image_layers_selected",
        False,
        "True when there is at least one selected layer and all selected layers are images",
    )
    only_labels_selected = RawContextKey(
        "only_labels_layers_selected",
        False,
        "True when there is at least one selected layer and all selected layers are labels",
    )
    image_active = RawContextKey(
        "active_layer_is_image",
        False,
        "True when the active layer is an image",
    )
    active_ndim = RawContextKey[Optional[int]](
        "active_layer_ndim",
        0,
        "Number of dimensions in the active layer, or None if nothing is active",
    )
    active_shape = RawContextKey[Optional[Tuple[int, ...]]](
        "active_layer_shape",
        (),
        "Shape of the active layer, or None if nothing is active.",
    )
    same_shape = RawContextKey(
        "all_layers_same_shape",
        False,
        "True when all selected layers have the same shape",
    )


class LayerListContextKeysManager:
    def __init__(
        self, layer_list: LayerList, context_key_service: ContextKeyService
    ) -> None:
        self._layer_list = layer_list

        srv = context_key_service
        context_key_service.create_key("LayerListId", f"LayerList:{id(layer_list)}")

        self._selection_count = LayerListContextKeys.selection_count.bind_to(srv)
        self._all_layers_linked = LayerListContextKeys.all_layers_linked.bind_to(srv)
        self._unselected_links = LayerListContextKeys.unselected_links.bind_to(srv)
        self._active_is_rgb = LayerListContextKeys.active_is_rgb.bind_to(srv)
        self._only_images_selected = LayerListContextKeys.only_images_selected.bind_to(
            srv
        )
        self._only_labels_selected = LayerListContextKeys.only_labels_selected.bind_to(
            srv
        )
        self._image_active = LayerListContextKeys.image_active.bind_to(srv)
        self._active_ndim = LayerListContextKeys.active_ndim.bind_to(srv)
        self._active_shape = LayerListContextKeys.active_shape.bind_to(srv)
        self._same_shape = LayerListContextKeys.same_shape.bind_to(srv)

        layer_list.selection.events.changed.connect(self._update_from_selection)
        self._update_from_selection()

    def _update_from_selection(self, event=None):
        from napari.layers.utils._link_layers import get_linked_layers, layer_is_linked

        s = self._layer_list.selection
        self._selection_count.set(len(s))
        self._all_layers_linked.set(bool(s and all(layer_is_linked(x) for x in s)))
        self._unselected_links.set(len(get_linked_layers(*s) - s))
        self._active_is_rgb.set(getattr(s.active, "rgb", False))
        self._only_images_selected.set(
            bool(s and all(x._type_string == "image") for x in s)
        )
        self._only_labels_selected.set(
            bool(s and all(x._type_string == "labels") for x in s)
        )
        self._image_active.set(bool(s.active and s.active._type_string == "Image"))
        self._active_ndim.set(s.active and getattr(s.active.data, "ndim", None))
        self._active_shape.set(s.active and getattr(s.active.data, "shape", None))
        self._same_shape.set(len({getattr(x.data, "shape", ()) for x in s}) == 1)


"""List model that also supports selection.

Events
------
inserting (index: int)
    emitted before an item is inserted at ``index``
inserted (index: int, value: T)
    emitted after ``value`` is inserted at ``index``
removing (index: int)
    emitted before an item is removed at ``index``
removed (index: int, value: T)
    emitted after ``value`` is removed at ``index``
moving (index: int, new_index: int)
    emitted before an item is moved from ``index`` to ``new_index``
moved (index: int, new_index: int, value: T)
    emitted after ``value`` is moved from ``index`` to ``new_index``
changed (index: int, old_value: T, value: T)
    emitted when ``index`` is set from ``old_value`` to ``value``
changed <OVERLOAD> (index: slice, old_value: List[_T], value: List[_T])
    emitted when ``index`` is set from ``old_value`` to ``value``
reordered (value: self)
    emitted when the list is reordered (eg. moved/reversed).

selection.changed (added: Set[_T], removed: Set[_T])
    Emitted when the set changes, includes item(s) that have been added
    and/or removed from the set.
selection.active (value: _T)
    emitted when the current item has changed.
selection._current (value: _T)
    emitted when the current item has changed. (Private event)
"""
