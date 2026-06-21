from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from src.shared.domain.entities import AggregateRoot, Entity
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError, NotFoundError
from src.shared.utils.time import current_datetime

from .events import (
    ProjectArchived,
    ProjectCreated,
    ProjectMembershipCreated,
    ProjectMembershipRemoved,
    ProjectStageCompleted,
    ProjectStageSkipped,
    ProjectStageStarted,
)
from .vo import ProjectKey, ProjectRole, ProjectStageStatus, ProjectStatus


@dataclass(kw_only=True)
class ProjectMembership(Entity):
    """
    Пользователь внутри проекта с выделенной ролью.
    Появляется в проекте через простое добавление.
    """

    project_id: UUID
    project_role: ProjectRole
    user_id: UUID
    created_by: UUID

    def remove(self, removed_by: UUID) -> None:
        if self.is_deleted:
            return

        self.deleted_at = current_datetime()

        self.register_event(
            ProjectMembershipRemoved(
                project_id=self.project_id,
                project_role=self.project_role,
                user_id=self.user_id,
                removed_by=removed_by,
            ),
        )


@dataclass(kw_only=True)
class ProjectStage(Entity):
    """
    Этап проекта - структурированный шаг в жизненном цикле проекта.
    """

    project_id: UUID
    name: str
    order: int

    status: ProjectStageStatus

    # Плановые даты (для планирования и диаграммы Ганта)
    planned_start: date | None = None
    planned_end: date | None = None

    # Фактические даты
    started_at: datetime | None = None
    completed_at: datetime | None = None
    responsible_id: UUID | None = None  # Ответственный за этап

    description: str | None = None
    completion_criteria: list[str] = field(default_factory=list)  # Критерии завершения

    def __post_init__(self) -> None:
        # Название этапа не может быть пустым
        if not self.name.strip():
            raise ValueError("Project stage name cannot be empty")

        # Порядковый номер этапа не может быть
        if self.order < 1:
            raise ValueError(
                "Project stage order cannot be less then 1. "
                "Order should be: 1; 2; 3; 4; ..."
            )

        # Плановая дата начала не может быть больше плановой даты завершения
        if self.planned_start is not None and self.planned_end is not None \
                and self.planned_start > self.planned_end:
            raise InvariantViolationError(
                "Planned planned_start date cannot be greater than planned planned_end date"
            )

        # Проект не может завершиться раньше, чам он начнётся
        if self.started_at is not None and self.completed_at is not None \
                and self.started_at > self.completed_at:
            raise InvariantViolationError("The project cannot be completed before it starts")

    @property
    def is_overdue(self) -> bool:
        """Просрочен ли срок выполнения"""

        today = current_datetime().date()
        return bool(self.planned_end is not None and today > self.planned_end)

    @property
    def planned_duration_days(self) -> int | None:
        """Продолжительность этапа в днях"""

        if self.planned_start is not None and self.planned_end is not None:
            return (self.planned_end - self.planned_start).days + 1

        return None

    def establish_planned_schedule(self, start: date, end: date) -> None:
        """Запланировать график проведения этапа"""

        if start > end:
            raise ValueError("Start planned date cannot be greater than planned planned_end date")

        # Нельзя сдвигать плановое начало этапа в прошлое, если этап уже начался
        if self.started_at is not None and start < self.started_at.date():
            raise InvariantViolationError("Cannot set planned end date before actual start date")

        self.planned_start = start
        self.planned_end = end
        self.updated_at = current_datetime()

    def edit(
            self,
            *,
            name: str | None = None,
            description: str | None = None,
            responsible_id: UUID | None = None,
            completion_criteria: list[str] | None = None,
    ) -> None:
        """Обновление справочной информации этапа"""

        changed = False

        if name is not None and name.strip() and name.strip() != self.name:
            self.name = name.strip()
            changed = True

        if description is not None and description.strip() \
                and description.strip() != self.description:
            self.description = description.strip()
            changed = True

        if responsible_id is not None and responsible_id != self.responsible_id:
            self.responsible_id = responsible_id
            changed = True

        if completion_criteria is not None and completion_criteria != self.completion_criteria:
            self.completion_criteria = completion_criteria
            changed = True

        if changed:
            self.updated_at = current_datetime()

    def start(self) -> None:
        """Начать этап проекта"""

        if self.status != ProjectStageStatus.PLANNED:
            raise InvalidStateError("Only PLANNED stage can be started")

        self.status = ProjectStageStatus.ACTIVE
        self.started_at = current_datetime()
        self.updated_at = current_datetime()

    def complete(self) -> None:
        if self.status != ProjectStageStatus.ACTIVE:
            raise InvalidStateError("Only ACTIVE stage can be completed")

        self.status = ProjectStageStatus.COMPLETED
        self.completed_at = current_datetime()
        self.updated_at = current_datetime()

    def skip(self) -> None:
        """Пропустить запланированный этап (без выполнения)"""

        if self.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}:
            raise InvalidStateError(f"Cannot skip a stage with status {self.status}")

        self.status = ProjectStageStatus.SKIPPED
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Project(AggregateRoot):
    """
    Проект - изолированный контейнер с процессами: тикеты, задачи, контекстные роли.
    """

    name: str
    key: ProjectKey  # Короткий уникальный ключ
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus

    owner_id: UUID
    created_by: UUID

    # Этапы проекта
    current_stage_id: UUID | None = None
    stages: list[ProjectStage] = field(default_factory=list)

    def __post_init__(self) -> None:
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
        project_id = uuid4()
        project = cls(
            id=project_id,
            name=name.strip(),
            key=ProjectKey(key),
            description=description,
            counterparty_id=counterparty_id,
            owner_id=created_by,
            status=ProjectStatus.ACTIVE,
            created_by=created_by,
        )

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
    ) -> ProjectMembership:
        """Создание участника в проекте"""

        # Нельзя создавать участников в архивном проекте
        if self.status == ProjectStatus.ARCHIVED:
            raise InvalidStateError("Cannot add member in ARCHIVED project")

        membership = ProjectMembership(
            project_id=self.id,
            user_id=user_id,
            project_role=project_role,
            created_by=created_by,
        )

        self.register_event(
            ProjectMembershipCreated(
                project_id=self.id,
                project_role=project_role,
                user_id=user_id,
                created_by=created_by,
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

    def _sort_stages(self) -> None:
        """Сортировка этапов проекта по их порядку"""

        self.stages.sort(key=lambda x: x.order)

    def add_stage(
            self,
            name: str,
            description: str | None = None,
            order: int | None = None,
            planned_start: date | None = None,
            planned_end: date | None = None,
    ) -> ProjectStage:
        """Добавление этапа в проект, по умолчанию добавление в коней списка этапов"""

        # Определение и валидация порядка этапа
        if order is None:
            order = len(self.stages) + 1
        elif order < 1:
            raise ValueError("Stage order must be >= 1")

        # Проверка порядка на уникальность
        if any(stage.order == order for stage in self.stages):
            raise InvariantViolationError(f"Stage with order {order} already exists")

        # Создание этапа
        stage = ProjectStage(
            project_id=self.id,
            name=name.strip(),
            description=description.strip(),
            order=order,
            status=ProjectStageStatus.PLANNED,
            planned_start=planned_start,
            planned_end=planned_end,
        )
        self.stages.append(stage)
        self.updated_at = current_datetime()

        # Сортировка по порядку
        self._sort_stages()

        return stage

    def reorder_stages(self, new_order: list[UUID]) -> None:
        """Изменение порядка этапов"""

        if len(new_order) != len(self.stages):
            raise ValueError("New order must contain all stages")

        # Проверка того, что все ID переданных этапов существуют
        stage_dict = {stage.id: stage for stage in self.stages}

        if set(new_order) != set(stage_dict.keys()):
            raise ValueError("Invalid stage IDs in new order")

        # Применение нового порядка
        self.stages = [stage_dict[stage_id] for stage_id in new_order]

        # Пересчёт порядка у всех этапов
        for i, stage in enumerate(self.stages, start=1):
            stage.order = i

    def _get_next_stage_order_to_start(self) -> int | None:
        """
        Возвращает порядковый номер следующего этапа, который можно начать.
        Все предыдущие этапы должны быть завершены.
        """

        sorted_stages = sorted(self.stages, key=lambda x: x.order)
        if not sorted_stages:
            return None

        for stage in sorted_stages:
            if stage.status == ProjectStageStatus.PLANNED:
                # Все предыдущие этапы должны быть завершены
                all_previous_completed = all(
                    prev_stage.status == ProjectStageStatus.COMPLETED
                    for prev_stage in sorted_stages
                    if prev_stage.order < stage.order
                )
                if all_previous_completed:
                    return stage.order

            # Есть активный этап - новый начинать нельзя
            elif stage.status == ProjectStageStatus.ACTIVE:
                return None

        return None

    def find_stage(self, stage_id: UUID) -> ProjectStage | None:
        return next((stage for stage in self.stages if stage.id == stage_id), None)

    def start_stage(self, stage_id: UUID, started_by: UUID) -> None:
        """Начать новую стадию проекта, необходимо закончить предыдущею"""

        stage = self.find_stage(stage_id)
        if not stage:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        # Можно начать только следующий по порядку этап
        excepted_order = self._get_next_stage_order_to_start()
        if excepted_order is None:
            raise InvalidStateError(
                "No stage can be started right now "
                "(maybe project is completed or an active stage exists)"
            )

        if stage.order != excepted_order:
            raise InvalidStateError(
                f"Cannot planned_start stage '{stage.name}' with order {stage.order}. "
                f"Excepted stage order - {excepted_order}"
            )

        stage.start()
        self.current_stage_id = stage.id
        self.updated_at = current_datetime()

        self.register_event(
            ProjectStageStarted(
                project_id=self.id,
                stage_id=stage.id,
                started_by=started_by,
            )
        )

    def _is_project_finalized(self) -> bool:
        """Завершён ли проект (все этапа должны быть пройдены)."""

        return all(
            stage.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}
            for stage in self.stages
        )

    def complete_stage(self, stage_id: UUID, completed_by: UUID) -> None:
        """Успешное завершение этапа проекта"""

        stage = self.find_stage(stage_id)
        if stage is None:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        # Этап должен быть активным для успешного завершения
        if stage.status != ProjectStageStatus.ACTIVE:
            raise InvalidStateError("Only ACTIVE stages can be completed")

        stage.complete()

        # Если это был последний этап - то проект успешно завершён
        # Перевод в статус - COMPLETED
        if self._is_project_finalized():
            self.status = ProjectStatus.COMPLETED

        # Обнуление текущей стадии, так как этап успешно завершён
        if self.current_stage_id == stage.id:
            self.current_stage_id = None

        self.updated_at = current_datetime()

        self.register_event(
            ProjectStageCompleted(
                project_id=self.id,
                stage_id=stage.id,
                completed_by=completed_by,
            )
        )

    def skip_stage(self, stage_id: UUID, skipped_by: UUID) -> None:
        """Пропуск этапа проекта"""

        stage = self.find_stage(stage_id)
        if stage is None:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        stage.skip()
        self.updated_at = current_datetime()

        if self.current_stage_id == stage.id:
            self.current_stage_id = None

        if self._is_project_finalized():
            self.status = ProjectStatus.COMPLETED

        self.register_event(
            ProjectStageSkipped(
                project_id=self.id,
                stage_id=stage.id,
                skipped_by=skipped_by,
            )
        )

    def remove_stage(self, stage_id: UUID) -> None:
        """Удаление этапа проекта"""

        stage = self.find_stage(stage_id)
        if stage is None:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        self.stages = [stage for stage in self.stages if stage.id != stage_id]

        self._sort_stages()
        for i, stage in enumerate(self.stages, start=1):
            stage.order = i
