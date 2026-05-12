from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.utils.time import current_datetime
from .events import MemberAdded, ProjectArchived, ProjectCreated
from .vo import ProjectKey, ProjectRole, ProjectStatus


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


@dataclass(kw_only=True)
class Project(AggregateRoot):
    """
    Проект - изолированный контейнер с процессами: тикеты, задачи, контекстные роли
    """

    name: str
    key: ProjectKey  # Короткий уникальный ключ
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus
    # Владелец проекта, руководитель или ответственный
    owner_id: UUID
    # Метаданные
    created_by: UUID

    def __post_init__(self) -> None:
        # Наименование проекта не может быть пустым
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")

    @classmethod
    def create(
            cls,
            name: str,
            key: str,
            created_by: UUID,
            description: str | None = None,
            counterparty_id: UUID | None = None,
    ) -> "Project":
        """Создание проекта"""

        project_id = uuid4()
        project = cls(
            id=project_id,
            name=name,
            key=ProjectKey(key),
            description=description,
            counterparty_id=counterparty_id,
            owner_id=created_by,
            status=ProjectStatus.ACTIVE,
            created_by=created_by,
        )

        # Регистрация доменного события
        project.register_event(
            ProjectCreated(
                project_id=project_id,
                name=name,
                owner_id=project.owner_id,
                created_by=created_by,
                counterparty_id=counterparty_id,
            )
        )

        return project

    def create_membership(
            self, user_id: UUID, project_role: ProjectRole, created_by: UUID
    ) -> Membership:
        """Создание участника в проекте"""

        membership = Membership(
            project_id=self.id,
            user_id=user_id,
            project_role=project_role,
            added_by=created_by,
        )

        # Регистрация доменного события
        self.register_event(
            MemberAdded(
                project_id=self.id,
                project_role=project_role,
                user_id=user_id,
                added_by=created_by,
            )
        )

        return membership

    def archive(self, archived_by: UUID) -> None:
        """Архивация проекта"""

        if not self.is_deleted:
            self.status = ProjectStatus.ARCHIVED
            self.deleted_at = current_datetime()

            self.register_event(
                ProjectArchived(project_id=self.id, archived_by=archived_by)
            )
