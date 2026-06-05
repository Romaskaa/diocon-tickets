from typing import Annotated

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, Field, NonNegativeInt

from .domain.vo import TimesheetStatus, WorklogStatus

TimesheetId = Annotated[UUID, Body(..., embed=True, description="ID ЛУРВ")]


class WorklogBase(BaseModel):
    """Базовая схема записи журнала потраченного времени"""

    ticket_id: UUID | None = Field(None, description="Тикет по которому выполнялись работы")
    task_id: UUID | None = Field(None, description="Задача по которой выполнялись работы")

    hours_spent: Decimal = Field(..., gt=0, description="Часов потрачено")
    entry_date: date = Field(..., description="Дата проведения работ")
    description: str = Field(..., description="Описание проведённых работ")


class WorklogCreate(WorklogBase):
    """
    Создание записи факта потраченных часов.
    Запись должна быть привязана к тикету или задаче (если задача привязана
    к тикету, то ID тикета указывать не нужно).
    """


class WorklogEdit(BaseModel):
    """Схема для редактирования записи"""

    hours_spent: Decimal | None = Field(None, gt=0, description="Часов потрачено")
    entry_date: date | None = Field(None, description="Дата проведения работ")
    description: str | None = Field(None, description="Описание проведённых работ")


class WorklogResponse(WorklogBase):
    """Схема ответа записи журнала времени"""

    id: UUID = Field(..., description="ID записи")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    timesheet_id: UUID | None = Field(None, description="ЛУРВ к которому привязана запись")
    status: WorklogStatus = Field(..., description="Текущий статус")

    approved_by: UUID | None = Field(
        None, description="Пользователь, который согласовал потраченный часы"
    )
    approved_at: datetime | None = Field(None, description="Время, когда были согласованы часы")
    rejection_reason: str | None = Field(None, description="Причина отклонения записи")


class TimesheetBase(BaseModel):
    """Базовая схема ЛУРВ"""

    period_start: date = Field(..., description="Дата начала периода")
    period_end: date = Field(..., description="Дата окончания периода")
    name: str = Field(
        ...,
        description="Наименование ЛУРВ",
        examples=["ЛУРВ за июнь по контрагенту «ДИО-Консалт»"],
    )
    counterparty_id: UUID | None = Field(
        None, description="Контрагент, по которому формируется ЛУРВ"
    )
    project_id: UUID | None = Field(None, description="Проект, по которому формируется ЛУРВ")


class TimesheetCreate(TimesheetBase):
    """
    Схема для создания ЛУРВ.
    Создаётся на основе записей о фактически затраченном времени за указанный период.
    """

    auto_add_worklogs: bool = Field(
        True, description="Автоматическое добавление рабочих журналов за указанный период"
    )


class TimesheetResponse(TimesheetBase):
    """Схема ответа ЛУРВ"""

    id: UUID = Field(..., description="ID ЛУРВ-а")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    user_id: UUID = Field(..., description="Пользователь, которому принадлежит ЛУРВ")
    status: TimesheetStatus = Field(..., description="Текущий статус")
    total_hours: Decimal = Field(..., description="Общее количество потраченных часов")
    approved_hours: Decimal = Field(..., description="Часов согласовано")
    pending_hours: Decimal = Field(..., description="Часов на согласовании")
    draft_hours: Decimal = Field(..., description="Часов в 'черновике'")

    worklog_ids: list[UUID] = Field(
        default_factory=list, description="Список записей факта потраченных часов"
    )
    worklogs_count: NonNegativeInt = Field(
        ..., description="Количество записей о факте потраченных часов"
    )

    submitted_at: datetime | None = Field(None, description="Дата отправки на согласование")
    approved_at: datetime | None = Field(None, description="Дата согласования")
    approved_by: UUID | None = Field(None, description="Тот кто согласовал часы")
