from typing import Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ....iam.domain.exceptions import PermissionDeniedError
from ....iam.domain.vo import UserRole
from ....shared.domain.entities import AggregateRoot, Entity
from ....shared.domain.exceptions import InvariantViolationError
from ....shared.utils.time import current_datetime
from ..events import ProjectCreated
from ..vo import ProjectKey, ProjectRole, ProjectStatus


@dataclass(kw_only=True)
class Membership(Entity):
    """
    Участник проекта
    """

    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    added_at: datetime = field(default_factory=current_datetime)
    added_by: UUID
    removed_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.removed_at is None


@dataclass(kw_only=True)
class Project(AggregateRoot):
    """
    Проект - контейнер для тикетов
    """

    name: str
    key: ProjectKey  # Короткий уникальный ключ
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus
    # Владелец проекта, руководитель или ответственный
    owner_id: UUID
    # Участники проекта (члены команды)
    memberships: list[Membership] = field(default_factory=list)
    # Метаданные
    created_by: UUID

    def __post_init__(self) -> None:
        # 1. Наименование проекта не может быть пустым
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")

        # 2. Владелец проекта должен быть среди его участников
        if not any(membership.user_id == self.owner_id for membership in self.memberships):
            raise InvariantViolationError("Owner must be a participant of the project")

    @classmethod
    def create(
            cls,
            name: str,
            key: str,
            owner_id: UUID,
            created_by: UUID,
            description: str | None = None,
            counterparty_id: UUID | None = None,
    ) -> Self:
        """Создание проекта"""

        project_id = uuid4()
        owner = Membership(
            project_id=project_id,
            user_id=owner_id,
            project_role=ProjectRole.OWNER,
            added_by=created_by,
        )
        project = cls(
            id=project_id,
            name=name,
            key=ProjectKey(key),
            description=description,
            counterparty_id=counterparty_id,
            owner_id=owner_id,
            status=ProjectStatus.ACTIVE,
            memberships=[owner],
            created_by=created_by,
        )
        project.register_event(
            ProjectCreated(
                project_id=project_id,
                name=name,
                created_by=created_by,
                counterparty_id=counterparty_id,
            )
        )
        return project

    def add_member(
            self,
            user_id: UUID,
            project_role: ProjectRole,
            added_by: UUID,
            added_by_role: UserRole,
    ) -> None:
        """Добавление участника"""

        # 1. Проверка прав на добавление
        if added_by != self.owner_id and added_by_role not in {
            UserRole.SUPPORT_MANAGER, UserRole.SUPPORT_AGENT, UserRole.ADMIN,
        }:
            raise PermissionDeniedError("Only owner or support stuff can add memberships")

        # 2. Проверка того, что участник уже есть
        if user_id in [membership.user_id for membership in self.memberships]:
            raise InvariantViolationError(f"User with ID {user_id} is already a member")

        self.memberships.append(
            Membership(
                project_id=self.id,
                user_id=user_id,
                project_role=project_role,
                added_by=added_by,
            )
        )
