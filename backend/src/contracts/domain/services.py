from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from .entities import ServiceContract

# Доменные сервисы для проверки прав доступа к договорам


def can_create_contract(user_role: UserRole) -> PermissionResult:
    """Может ли пользователь создавать новый договор"""

    if user_role not in {UserRole.ACCOUNT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(False, "Only account manager or above can create contracts")

    return PermissionResult(True)


def can_view_contract(
        contract: ServiceContract,
        user_role: UserRole,
        user_counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Может ли пользователь просматривать договор"""

    # 1. Внутренние менеджеры могут просматривать договор
    if user_role in {
        UserRole.ADMIN,
        UserRole.ACCOUNT_MANAGER,
        UserRole.FINANCE,
        UserRole.SUPPORT_MANAGER,
    }:
        return PermissionResult(True)

    # 2. Клиенты могут просматривать договор только для своего контрагента
    if user_role.is_customer():
        if contract.counterparty_id != user_counterparty_id:
            return PermissionResult(
                False, "Customers can view contracts issued to his counterparty"
            )
        return PermissionResult(True)

    # 3. Запрет для остальных случаев
    return PermissionResult(False, "Insufficient rights to view contracts")


def can_manage_packages(user_role: UserRole) -> PermissionResult:
    """Может ли пользователь добавлять / изменять пакеты часов в договоре"""

    # Только менеджер по работе с клиентами или выше может работать с пакетами часов
    if user_role not in {UserRole.ACCOUNT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(False, "Only account manager or above can manage packages")

    return PermissionResult(True)
