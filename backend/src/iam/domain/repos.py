from typing import Protocol, override

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from ..domain.vo import UserRole
from .entities import Invitation, User


class UserRepository(Repository[User]):

    @override
    async def paginate(
            self, params: PageParams, include_roles: list[UserRole] | None = None
    ) -> Page[User]:
        """
        Переопределённая пагинация с фильтром по ролям
        """

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_customer_admins(
            self, counterparty_id: UUID, role: UserRole | None = None
    ) -> list[User]:
        """
        Получение всех администраторов клиента привязанных к контрагенту
        """

    async def get_customers(self, counterparty_id: UUID) -> Page[User]:
        """Получение всех клиентов привязанных к контрагенту"""


class TokenBlacklist(Protocol):

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        """Отзыв токена (добавление токена в черный список)"""

    async def is_revoked(self, jti: UUID) -> bool:
        """Проверка токена на отзыв"""


class InvitationRepository(Repository[Invitation]):

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None: ...
