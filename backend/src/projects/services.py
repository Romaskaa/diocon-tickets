import random
import string
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..iam.domain.exceptions import PermissionDeniedError
from ..iam.schemas import CurrentUser
from ..shared.domain.events import EventPublisher
from ..shared.domain.exceptions import AlreadyExistsError, NotFoundError
from ..shared.schemas import Page
from .domain.entities import Project
from .domain.repos import MembershipRepository, ProjectRepository
from .domain.services import ProjectAccessService
from .domain.vo import ProjectKey, ProjectRole
from .mappers import (
    map_membership_to_response,
    map_project_to_detailed_response,
    map_project_to_response,
)
from .schemas import (
    KeyCheckResult,
    MemberCreate,
    MembershipResponse,
    ProjectCreate,
    ProjectDetailedResponse,
    ProjectResponse,
)


class ProjectService:
    def __init__(
            self,
            session: AsyncSession,
            project_repo: ProjectRepository,
            membership_repo: MembershipRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.project_repo = project_repo
        self.membership_repo = membership_repo
        self.access_service = ProjectAccessService(membership_repo)
        self.event_publisher = event_publisher

    async def generate_key_suggestions(
            self, original_key: str, max_attempts: int = 5, min_key_length: int = 3
    ) -> list[str]:
        """
        Генерация списка альтернативных ключей проекта в стиле Jira.
        Для избежания коллизий при создании проекта.

        Примеры:
         - original_key = "WEB" -> ["WEB1", "WEB2", "WEB3", "WEB-1", "WEB-2", ...]
         - original_key = "CRM" -> ["CRM1", "CRM2", "CRM3", ...]
        """

        base_key = original_key.strip().upper()

        if not base_key:
            base_key = "PROJ"  # fallback

        # 1. Добавление простых числовых суффиксов
        suggestions = [f"{base_key}{i}" for i in range(1, max_attempts + 1)]

        # 2. Если ключ короткий, то добавление вариантов с буквами
        if len(base_key) <= min_key_length:
            alphabet = string.ascii_uppercase
            suggestions.extend(
                f"{base_key}{letter}" for letter in random.sample(alphabet, len(alphabet))
            )

        # 3. Удаление дубликатов и сохранение порядка
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)

        unique_suggestions = unique_suggestions[: max_attempts * 2]

        existing_keys = await self.project_repo.get_existing_keys(unique_suggestions)

        # Получение только свободных
        available = [key for key in unique_suggestions if key not in existing_keys]

        return available[:max_attempts]

    async def check_key(self, project_key: str) -> KeyCheckResult:
        """Проверка ключа на уникальность перед созданием"""

        # 1. Если проекта нет - то ключ свободен
        project_key = ProjectKey(project_key)
        project = await self.project_repo.get_by_key(project_key)
        if project is None:
            return KeyCheckResult(available=True)

        # 2. Генерация альтернатив
        suggestions = await self.generate_key_suggestions(project_key.value)
        return KeyCheckResult(available=False, suggestions=suggestions)

    async def create(
            self, data: ProjectCreate, current_user: CurrentUser, max_attempts: int = 5,
    ) -> ProjectDetailedResponse:
        """
        Создание проекта с уникальным ключом
        """

        # 1. Проверка прав на создание проекта
        permission = self.access_service.can_create_project(
            user_role=current_user.role, project_counterparty_id=data.counterparty_id
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 2. Создание с retires попытками для разрешения коллизий на уникальность ключа
        original_key, key_candidate = data.key, data.key
        for attempt in range(1, max_attempts + 1):
            try:
                project = Project.create(
                    name=data.name,
                    key=key_candidate,
                    description=data.description,
                    counterparty_id=data.counterparty_id,
                    created_by=current_user.user_id,
                )
                await self.project_repo.create(project)
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                key_candidate = f"{original_key}{attempt}"

            # 3. Добавление владельца проекта и фиксация изменений
            else:
                owner = project.create_membership(
                    user_id=current_user.user_id,
                    project_role=ProjectRole.OWNER,
                    created_by=current_user.user_id,
                )
                await self.membership_repo.create(owner)
                await self.session.commit()

                # 4. Публикация доменных событий
                for event in project.collect_events():
                    await self.event_publisher.publish(event)

                # 5. Формирование ответа
                memberships = [owner]
                return map_project_to_detailed_response(
                    project, memberships=Page.create(
                        memberships, total_items=len(memberships), page=1, size=1,
                    )
                )

        raise AlreadyExistsError(
            f"Project with key - {key_candidate} already exists. "
            f"{max_attempts} attempts were not enough to resolve the uniqueness of the key. "
            f"Try again with a different key.",
            details={"last_suggested_key": key_candidate},
        )

    async def add_member(
            self, project_id: UUID, data: MemberCreate, current_user: CurrentUser
    ) -> MembershipResponse:
        """Добавление участника в проект"""

        # 1. Получение и проверка на существование
        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        # 2. Проверка прав на добавление участника
        permission = await self.access_service.can_add_members(
            project=project,
            target_role=data.project_role,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Был ли такой участник уже добавлен в проект
        existing = await self.membership_repo.find(project_id, data.user_id)
        if existing is not None:
            raise AlreadyExistsError(f"User with ID {current_user.user_id} is already a member")

        # 4. Создание и сохранение сущности
        membership = project.create_membership(
            user_id=data.user_id,
            project_role=data.project_role,
            created_by=current_user.user_id,
        )
        await self.membership_repo.create(membership)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_membership_to_response(membership)

    async def archive(self, project_id: UUID, current_user: CurrentUser) -> ProjectResponse:
        """Архивирование проекта (soft-delete)"""

        # 1. Получение и проверка на существование
        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        # 2. Проверка прав на архивирование проекта
        permission = self.access_service.can_archive_project(
            project=project,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Архивация и обновление сущности
        project.archive(archived_by=current_user.user_id)
        await self.project_repo.upsert(project)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_project_to_response(project)
