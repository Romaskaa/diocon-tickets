from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from typing_extensions import Doc

from src.shared.domain.entities import AggregateRoot, Entity
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError, NotFoundError
from src.shared.utils.time import current_datetime

from .events import (
    ProjectArchived,
    ProjectCreated,
    ProjectMemberCreated,
    ProjectMemberRemoved,
)
from .vo import ProjectKey, ProjectRole, ProjectStageStatus, ProjectStatus


@dataclass(kw_only=True)
class ProjectMember(Entity):
    """
    Участник проекта, имеет ограниченный набор ролей в рамках одного проекта.
    """

    project_id: UUID
    project_roles: list[ProjectRole]
    user_id: UUID
    created_by: UUID

    def has_role(self, project_role: ProjectRole) -> bool:
        return project_role in self.project_roles

    def grant_role(self, project_role: ProjectRole) -> None:
        if project_role in self.project_roles:
            return

        self.project_roles.append(project_role)
        self.updated_at = current_datetime()

    def remove(self, removed_by: UUID) -> None:
        if self.is_deleted:
            return

        self.deleted_at = current_datetime()

        self.register_event(
            ProjectMemberRemoved(
                project_id=self.project_id,
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
    execution_order: Annotated[
        int,
        Doc("Группа/волна выполнения. Этапы с одинаковым execution_order могут идти параллельно")
    ]

    status: ProjectStageStatus

    planned_start: Annotated[date | None, Doc("Плановая дата начала")] = None
    planned_end: Annotated[date | None, Doc("Плановая дата завершения")] = None

    started_at: Annotated[datetime | None, Doc("Фактическое время начала")] = None
    completed_at: Annotated[datetime | None, Doc("Фактическое время завершения")] = None
    responsible_id: Annotated[UUID | None, Doc("Ответственный за этап")] = None

    description: str | None = None
    completion_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Project stage name cannot be empty")

        if self.execution_order < 1:
            raise ValueError(
                "Project stage execution execution_order cannot be less then 1. "
                "Execution execution_order should be: 1; 2; 3; 4; ..."
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
        """
        Просрочен ли срок выполнения.
        """

        today = current_datetime().date()
        return bool(self.planned_end is not None and today > self.planned_end)

    @property
    def planned_duration_days(self) -> int | None:
        """
        Плановая продолжительность этапа в днях.
        """

        if self.planned_start is not None and self.planned_end is not None:
            return (self.planned_end - self.planned_start).days + 1

        return None

    def establish_planned_schedule(self, start: date, end: date) -> None:
        """
        Запланировать график проведения этапа.
        """

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
        """
        Обновить справочную информацию этапа.
        """

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
        """
        Начать этап проекта.
        """

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
        """
        Пропустить запланированный этап (без выполнения).
        """

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
    key: ProjectKey
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus

    owner_id: UUID
    created_by: UUID

    stages: list[ProjectStage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")

    @classmethod
    def create(
            cls,
            name: str,
            key: ProjectKey,
            created_by: UUID,
            description: str | None = None,
            counterparty_id: UUID | None = None,
    ) -> Self:
        stripped_name = name.strip()
        project = cls(
            name=stripped_name,
            key=key,
            description=description,
            counterparty_id=counterparty_id,
            owner_id=created_by,
            status=ProjectStatus.ACTIVE,
            created_by=created_by,
        )
        project.register_event(
            ProjectCreated(
                project_id=project.id,
                name=name,
                owner_id=project.owner_id,
                created_by=created_by,
                counterparty_id=counterparty_id,
            )
        )
        return project

    def create_member(
            self, user_id: UUID, project_roles: list[ProjectRole], created_by: UUID
    ) -> ProjectMember:
        """
        Создание участника в проекте (фабричный метод).
        """

        if self.status == ProjectStatus.ARCHIVED:
            raise InvalidStateError("Cannot add member in ARCHIVED project")

        unique_project_roles = set(project_roles)

        if len(unique_project_roles) > len(ProjectRole):
            raise InvariantViolationError("Too many project roles granted")

        member = ProjectMember(
            project_id=self.id,
            project_roles=list(project_roles),
            user_id=user_id,
            created_by=created_by,
        )

        self.register_event(
            ProjectMemberCreated(
                project_id=self.id,
                user_id=user_id,
                created_by=created_by,
            )
        )

        return member

    def archive(self, archived_by: UUID) -> None:
        """
        Архивирование проекта (мягкое удаление).
        """

        if self.is_deleted:
            return

        self.status = ProjectStatus.ARCHIVED
        self.deleted_at = current_datetime()

        self.register_event(
            ProjectArchived(project_id=self.id, archived_by=archived_by)
        )

    @property
    def active_stages(self) -> list[ProjectStage]:
        """
        Получить список активных этапов.
        """

        return [stage for stage in self.stages if stage.status == ProjectStageStatus.ACTIVE]

    def get_stages_by_execution_order(self, execution_order: int) -> list[ProjectStage]:
        """
        Получить этапы по порядку их выполнения.
        """

        return [stage for stage in self.stages if stage.execution_order == execution_order]

    def get_last_execution_order(self) -> int:
        """
        Получить порядковый номер последнего этапа.
        """

        if not self.stages:
            return 0

        return max(stage.execution_order for stage in self.stages)

    def is_execution_order_completed(self, execution_order: int) -> bool:
        """
        Все ли этапы данной группы завершены или пропущены.
        """

        stages = self.get_stages_by_execution_order(execution_order)
        if not stages:
            return False

        return all(
            stage.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}
            for stage in stages
        )

    def get_next_executable_order(self) -> int | None:
        """
        Возвращает следующий этап который можно начинать.
        """

        if not self.stages:
            return None

        max_order = self.get_last_execution_order()

        for order in range(1, max_order + 1):
            group_stage = self.get_stages_by_execution_order(order)

            if any(stage.status == ProjectStageStatus.ACTIVE for stage in group_stage):
                return None

            if not self.is_execution_order_completed(order) and \
                    all(self.is_execution_order_completed(prev) for prev in range(1, order)):
                return order

        return None

    def _sort_stages(self) -> None:
        """
        Сортировка этапов проекта по их порядку.
        """

        self.stages.sort(key=lambda x: x.execution_order)

    def add_stage(
        self,
        name: str,
        execution_order: int,
        description: str | None = None,
        planned_start: date | None = None,
        planned_end: date | None = None,
        responsible_id: UUID | None = None,
    ) -> ProjectStage:
        """
        Добавить новый этап в проект.
        """

        if execution_order < 1:
            raise ValueError("Execution execution_order must be positive")

        if any(stage.name.lower() == name.strip().lower() for stage in self.stages):
            raise ValueError(f"Project stage with this name - {name} already exists")

        stage = ProjectStage(
            project_id=self.id,
            name=name.strip(),
            description=description.strip(),
            execution_order=execution_order,
            status=ProjectStageStatus.PLANNED,
            planned_start=planned_start,
            planned_end=planned_end,
            responsible_id=responsible_id,
        )
        self.stages.append(stage)
        self._sort_stages()
        self.updated_at = current_datetime()

        return stage

    def reorder_stages(self, stage_groups: list[list[UUID]]) -> None:
        """
        Перестраивает этапы проекта с явным указанием групп выполнения.
        """

        if not stage_groups:
            raise ValueError("Stage groups cannot be empty")

        all_stage_ids: set[UUID] = set()
        for group in stage_groups:
            if not group:
                raise ValueError("Empty group in stage groups is not allowed")

            for stage_id in group:
                if stage_id in all_stage_ids:
                    raise InvariantViolationError(f"Stage {stage_id} appears more than once")

                all_stage_ids.add(stage_id)

        if len(all_stage_ids) != len(self.stages):
            raise InvariantViolationError(
                f"Stage groups must contain all stages exactly once. "
                f"Expected {len(self.stages)}, got {len(all_stage_ids)}"
            )

        stages_dict = {stage.id: stage for stage in self.stages}
        missing = all_stage_ids - set(stages_dict.keys())
        if missing:
            raise NotFoundError(f"Some stages not found: {missing}")

        new_stages: list[ProjectStage] = []

        for i, group in enumerate(stage_groups, start=1):
            for stage_id in group:
                stage = stages_dict[stage_id]
                stage.execution_order = i
                new_stages.append(stage)

        self.stages = new_stages

        self._sort_stages()
        self.updated_at = current_datetime()

    def find_stage(self, stage_id: UUID) -> ProjectStage | None:
        return next((stage for stage in self.stages if stage.id == stage_id), None)

    def start_stage(self, stage_id: UUID) -> None:
        """
        Начать новую стадию проекта.
        """

        stage = self.find_stage(stage_id)
        if not stage:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        next_order = self.get_next_executable_order()
        if next_order is None:
            raise InvalidStateError(
                "Cannot start any stage at the moment "
                "(previous groups not completed or active stages exist)"
            )

        if stage.execution_order != next_order:
            raise InvalidStateError(
                f"Cannot start stage '{stage.name}'. "
                f"Next available execution_order is {next_order}"
            )

        stage.start()
        self.updated_at = current_datetime()

    def complete_stage(self, stage_id: UUID) -> None:
        """
        Успешно завершает этап.
        """

        stage = self.find_stage(stage_id)
        if not stage:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        if stage.status != ProjectStageStatus.ACTIVE:
            raise InvalidStateError("Only ACTIVE stage can be completed")

        stage.complete()

        # Проверяем, не завершился ли весь проект
        if all(
            stage.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}
            for stage in self.stages
        ):
            self.status = ProjectStatus.COMPLETED

        self.updated_at = current_datetime()

    def remove_stage(self, stage_id: UUID) -> None:
        """
        Удалить этап проекта (удалять можно только запланированные или пропущенные этапы).
        """

        stage = self.find_stage(stage_id)
        if stage is None:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist in project")

        if stage.status in {ProjectStageStatus.ACTIVE, ProjectStageStatus.COMPLETED}:
            raise InvalidStateError("Only PLANNED or SKIPPED stages can be removed")

        self.stages.remove(stage)

        for i, stage in enumerate(sorted(self.stages, key=lambda s: s.execution_order), start=1):
            stage.order = i

        self.updated_at = current_datetime()

    def skip_stage(self, stage_id: UUID) -> None:
        """
        Пропустить этап проекта.

        Правила:
        - Можно пропустить только этап из следующей доступной группы (execution_order)
        - В группе уже не должно быть ACTIVE этапов
        - Все предыдущие группы должны быть завершены
        """

        stage = self.find_stage(stage_id)
        if stage is None:
            raise NotFoundError(f"Stage with ID {stage_id} does not exist")

        if stage.status != ProjectStageStatus.PLANNED:
            raise InvalidStateError(
                f"Only PLANNED stages can be skipped. Current status: {stage.status}"
            )

        next_executable_order = self.get_next_executable_order()

        if next_executable_order is None:
            raise InvalidStateError(
                "No stage can be skipped at the moment. "
                "Either all stages are completed or there are active stages."
            )

        if stage.execution_order != next_executable_order:
            raise InvalidStateError(
                f"Cannot skip stage '{stage.name}' (execution_order={stage.execution_order}). "
                f"Next available execution_order is {next_executable_order}."
            )

        stage.skip()
        self.updated_at = current_datetime()

        # Проверяем, не завершился ли проект после пропуска
        if all(
            s.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}
            for s in self.stages
        ):
            self.status = ProjectStatus.COMPLETED
