from typing import TYPE_CHECKING

from ...shared.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from .states import TicketState
    from .vo import TicketStatus

_state_registry: dict["TicketStatus", type["TicketState"]] = {}


def register_state(status: "TicketStatus"):
    """
    Декоратор для регистрации реализации класса состояния.
    """

    def decorator(state_class: type["TicketState"]) -> type["TicketState"]:
        _state_registry[status] = state_class
        return state_class

    return decorator


def get_state(status: "TicketStatus") -> "TicketState":
    """
    Возвращает экземпляр зарегистрированного состояния по статусу.
    """

    state_class = _state_registry.get(status)
    if state_class is None:
        raise InvalidStateError(f"Not registered state for status - `{status.value}`")

    return state_class()
