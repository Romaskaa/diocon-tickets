from typing import TypeVar

from collections.abc import Callable

from src.shared.domain.events import Event

from .domain.models import ActivityLog

EventType = TypeVar("EventType", bound=Event)

ActivityMapper = Callable[[EventType], ActivityLog]

_activity_mappers_registry: dict[type[EventType], ActivityMapper] = {}


def register[T: Event](event_type: type[T]) -> Callable[[ActivityMapper[T]], ActivityMapper[T]]:

    def decorator(func: ActivityMapper[T]) -> ActivityMapper[T]:
        _activity_mappers_registry[event_type] = func
        return func

    return decorator


def map_event_to_activity_log[T: Event](event: T) -> ActivityLog:
    return _activity_mappers_registry[type(event)](event)
