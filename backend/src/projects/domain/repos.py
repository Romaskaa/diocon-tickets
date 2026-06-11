from typing import override

from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, Pagination
from .entities import Project, ProjectMembership
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
            pagination: Pagination,
            owner_only: bool = False,
    ) -> Page[Project]:
        """
        Получение проектов в которых состоит пользователь
        """


class MembershipRepository(Repository[ProjectMembership]):

    @override
    async def paginate(
            self,
            pagination: Pagination,
            project_id: UUID | None = None,
            include_project_roles: list[ProjectRole] | None = None,
    ) -> Page[ProjectMembership]: ...

    async def find(self, project_id: UUID, user_id: UUID) -> ProjectMembership | None:
        """Поиск участника внутри проекта по уникальной комбинации"""

    async def get_by_user(self, user_id: UUID) -> list[ProjectMembership]:
        """
        Возвращает все членства пользователя во всех проектах.
        Используется для получения полного списка проектов пользователя
        (например, для построения селектора проектов или персональной панели).
        """
