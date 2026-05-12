from typing import override

from uuid import UUID

from sqlalchemy import and_, exists, or_, select

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Membership, Project
from ..domain.vo import ProjectKey, ProjectRole
from .models import MembershipOrm, ProjectOrm


class MembershipMapper(ModelMapper[Membership, MembershipOrm]):
    @staticmethod
    def to_entity(model: MembershipOrm) -> Membership:
        return Membership(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            project_id=model.project_id,
            user_id=model.user_id,
            project_role=model.project_role,
            added_at=model.added_at,
            added_by=model.added_by,
        )

    @staticmethod
    def from_entity(entity: Membership) -> MembershipOrm:
        return MembershipOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            project_id=entity.project_id,
            project_role=entity.project_role,
            added_at=entity.added_at,
            added_by=entity.added_by,
        )


class ProjectMapper(ModelMapper[Project, ProjectOrm]):
    @staticmethod
    def to_entity(model: ProjectOrm) -> Project:
        return Project(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            created_by=model.created_by,
            name=model.name,
            description=model.description,
            key=ProjectKey(model.key),
            counterparty_id=model.counterparty_id,
            owner_id=model.owner_id,
            status=model.status,
        )

    @staticmethod
    def from_entity(entity: Project) -> ProjectOrm:
        return ProjectOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            created_by=entity.created_by,
            name=entity.name,
            key=entity.key.value,
            description=entity.description,
            counterparty_id=entity.counterparty_id,
            owner_id=entity.owner_id,
            status=entity.status,
        )


class SqlProjectRepository(SqlAlchemyRepository[Project, ProjectOrm]):
    model = ProjectOrm
    model_mapper = ProjectMapper

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        stmt = select(self.model).where(self.model.key == key.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        if not keys:
            return set()

        stmt = select(self.model.key).where(self.model.key.in_(keys))
        result = await self.session.execute(stmt)

        return {row[0] for row in result.all()}

    async def get_by_user_membership(
        self,
        user_id: UUID,
        pagination: PageParams,
        owner_only: bool = False,
    ) -> Page[Project]:
        # 1. Базовый запрос + проверка наличия членства в проекте
        stmt = select(self.model)
        membership_exists = exists().where(
            and_(
                MembershipOrm.project_id == self.model.id,
                MembershipOrm.user_id == user_id,
                MembershipOrm.deleted_at.is_(None),
            )
        )

        # 2. Добавление фильтра, если нужны только проекты, где пользователь владелец
        if owner_only:
            stmt = stmt.where(self.model.owner_id == user_id)
        else:
            stmt = stmt.where(or_(self.model.owner_id == user_id, membership_exists))

        return await self._paginate(stmt, pagination)


class SqlMembershipRepository(SqlAlchemyRepository[Membership, MembershipOrm]):
    model = MembershipOrm
    model_mapper = MembershipMapper

    @override
    async def paginate(
            self,
            pagination: PageParams,
            project_id: UUID | None = None,
            include_project_roles: list[ProjectRole] | None = None,
    ) -> Page[Membership]:
        # 1. Базовый запрос для получения всех участников
        stmt = select(self.model)

        # 2. Применение фильтров
        if project_id is not None:
            stmt = stmt.where(self.model.project_id == project_id)

        if include_project_roles is not None:
            stmt = stmt.where(self.model.project_role.in_(include_project_roles))

        return await self._paginate(stmt, pagination)

    async def find(self, project_id: UUID, user_id: UUID) -> Membership | None:
        stmt = select(self.model).where(
            (self.model.project_id == project_id) & (self.model.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
