import random
import string
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.domain.vo import UserRole
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import AlreadyExistsError, NotFoundError
from ..domain.entities import Project
from ..domain.repos import ProjectRepository
from ..domain.vo import ProjectKey
from ..mappers import map_project_to_response
from ..schemas import KeyCheckResponse, MembersAdd, ProjectCreate, ProjectResponse

# Длина короткого ключа проекта
SHORT_PROJECT_KEY_LENGTH = 3


class ProjectService:
    def __init__(
            self,
            session: AsyncSession,
            repository: ProjectRepository,
            event_publisher: EventPublisher
    ) -> None:
        self.session = session
        self.repository = repository
        self.event_publisher = event_publisher

    async def check_key(self, project_key: str) -> KeyCheckResponse:

        # 1. Проверка текущего проекта
        project_key = ProjectKey(project_key)
        project = await self.repository.get_by_key(project_key)
        if project is None:
            return KeyCheckResponse(available=True)

        # 2. Генерация альтернатив
        suggestions = await self.generate_key_suggestions(project_key.value)
        return KeyCheckResponse(available=False, suggestions=suggestions)

    async def generate_key_suggestions(
            self, original_key: str, max_attempts: int = 5
    ) -> list[str]:
        """
        Генерация списка альтернативных ключей проекта в стиле Jira.

        Примеры:
         - original_key = "WEB"   →  ["WEB1", "WEB2", "WEB3", "WEB-1", "WEB-2", ...]
         - original_key = "CRM"   →  ["CRM1", "CRM2", "CRM3", ...]
        """

        base_key = original_key.strip().upper()

        if not base_key:
            base_key = "PROJ"  # fallback

        # 1. Добавление простых числовых суффиксов
        suggestions = [f"{base_key}{i}" for i in range(1, max_attempts + 1)]

        # 2. Если ключ короткий, то добавление вариантов с буквами
        if len(base_key) <= SHORT_PROJECT_KEY_LENGTH:
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

        unique_suggestions = unique_suggestions[:max_attempts * 2]

        existing_keys = await self.repository.get_existing_keys(unique_suggestions)

        # Получение только свободных
        available = [key for key in unique_suggestions if key not in existing_keys]

        return available[:max_attempts]

    async def create(
            self, data: ProjectCreate, created_by: UUID, max_attempts: int = 5
    ) -> ProjectResponse:
        """
        Создание проекта с уникальным ключом
        """

        original_key, key_candidate = data.key, data.key
        for attempt in range(1, max_attempts + 1):
            try:
                project = Project.create(
                    name=data.name,
                    key=key_candidate,
                    description=data.description,
                    counterparty_id=data.counterparty_id,
                    owner_id=data.owner_id,
                    created_by=created_by,
                )
                await self.repository.create(project)
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                key_candidate = f"{original_key}{attempt}"
            else:
                await self.session.commit()
                return map_project_to_response(project)
        raise AlreadyExistsError(
            f"Project with key - {key_candidate} already exists. "
            f"{max_attempts} attempts were not enough to resolve the uniqueness of the key. "
            f"Try again with a different key.",
            details={"last_suggested_key": key_candidate}
        )

    async def add_members(
            self, project_id: UUID, data: MembersAdd, added_by: UUID, added_by_role: UserRole
    ) -> ProjectResponse:
        """Добавление участников в проект"""

        # 1. Получение проекта
        project = await self.repository.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        # 2. Добавление участников и обновление сущности
        for member in data.members:
            project.add_member(
                user_id=member.user_id,
                project_role=member.project_role,
                added_by=added_by,
                added_by_role=added_by_role,
            )
        await self.repository.upsert(project)
        await self.session.commit()

        # 3. Публикация доменных событий
        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_project_to_response(project)
