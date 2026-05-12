from typing import override

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Membership, Project
from .vo import ProjectKey, ProjectRole


class ProjectRepository(Repository[Project]):

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        """Получение проекта по его уникальному ключу"""

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        """
        Возвращает множество ключей, которые уже существуют.
        Оптимизировано для пакетной проверки.
        """

    async def get_by_user_membership(
            self,
            user_id: UUID,
            pagination: PageParams,
            owner_only: bool = False,
    ) -> Page[Project]:
        """
        Получение проектов в которых состоит пользователь
        """


class MembershipRepository(Repository[Membership]):

    @override
    async def paginate(
            self,
            pagination: PageParams,
            project_id: UUID | None = None,
            include_project_roles: list[ProjectRole] | None = None,
    ) -> Page[Membership]: ...

    async def find(self, project_id: UUID, user_id: UUID) -> Membership | None:
        """Поиск участника внутри проекта по уникальной комбинации"""
