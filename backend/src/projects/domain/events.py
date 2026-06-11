from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import ProjectRole


@dataclass(frozen=True, kw_only=True)
class ProjectCreated(Event):
    """Проект успешно создан"""

    project_id: UUID
    name: str
    created_by: UUID
    owner_id: UUID
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class MemberAdded(Event):
    """Участник добавлен в проект"""

    project_id: UUID
    project_role: ProjectRole
    user_id: UUID
    added_by: UUID


@dataclass(frozen=True, kw_only=True)
class ProjectArchived(Event):
    """Проект перенесён в архив"""

    project_id: UUID
    archived_by: UUID


@dataclass(frozen=True, kw_only=True)
class ProjectStageStarted(Event):
    """Начался новый этап проекта"""

    project_id: UUID
    stage_id: UUID
    started_by: UUID


@dataclass(frozen=True, kw_only=True)
class ProjectStageCompleted(Event):
    """Этап проекта успешно завершён"""

    project_id: UUID
    stage_id: UUID
    completed_by: UUID
