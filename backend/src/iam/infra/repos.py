from typing import override

from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Invitation, User
from ..domain.vo import FullName, Username, UserRole
from .models import InvitationOrm, UserOrm


class UserMapper(ModelMapper[User, UserOrm]):
    @staticmethod
    def to_entity(model: UserOrm) -> User:
        return User(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=model.email,
            username=None if model.username is None else Username(model.username),
            full_name=None if model.full_name is None else FullName(model.full_name),
            avatar_url=model.avatar_url,
            counterparty_id=model.counterparty_id,
            role=model.role,
            password_hash=SecretStr(model.password_hash),
            is_active=model.is_active,
        )

    @staticmethod
    def from_entity(entity: User) -> UserOrm:
        return UserOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            email=entity.email,
            username=None if entity.username is None else entity.username.value,
            full_name=None if entity.full_name is None else entity.full_name.value,
            avatar_url=entity.avatar_url,
            counterparty_id=entity.counterparty_id,
            role=entity.role,
            password_hash=entity.password_hash.get_secret_value(),
            is_active=entity.is_active,
        )


class SqlUserRepository(SqlAlchemyRepository[User, UserOrm]):
    model = UserOrm
    model_mapper = UserMapper

    @override
    async def paginate(
            self, params: PageParams, include_roles: list[UserRole] | None = None
    ) -> Page[User]:
        stmt = select(self.model)
        if include_roles is not None:
            stmt = stmt.where(self.model.role.in_(include_roles))

        return await self._paginate(stmt, params)

    async def get_by_email(self, email: str) -> User:
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_customer_admins(self, counterparty_id: UUID) -> list[User]:
        stmt = select(self.model).where(
            (self.model.counterparty_id == counterparty_id) &
            (self.model.role == UserRole.CUSTOMER_ADMIN)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.to_entity(model) for model in models]


class InvitationMapper(ModelMapper[Invitation, InvitationOrm]):
    @staticmethod
    def to_entity(model: InvitationOrm) -> Invitation:
        return Invitation(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=model.email,
            token=model.token,
            invited_by=model.invited_by,
            assigned_role=model.assigned_role,
            counterparty_id=model.counterparty_id,
            expires_at=model.expires_at,
            used_at=model.used_at,
            is_used=model.is_used,
        )

    @staticmethod
    def from_entity(entity: Invitation) -> InvitationOrm:
        return InvitationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            email=entity.email,
            token=entity.token,
            invited_by=entity.invited_by,
            assigned_role=entity.assigned_role,
            counterparty_id=entity.counterparty_id,
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            is_used=entity.is_used,
        )


class SqlInvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    model = InvitationOrm
    model_mapper = InvitationMapper

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(self.model.token == token)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email) &
                (self.model.assigned_role == user_role) &
                (self.model.is_used.is_(False))
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
