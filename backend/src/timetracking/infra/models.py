from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import TEXT, Date, DateTime, Enum, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.database import Base
from ..domain.vo import TimesheetStatus, WorklogStatus


class WorklogOrm(Base):
    __tablename__ = "worklogs"

    timesheet_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("timesheets.id", ondelete="SET NULL"), nullable=True
    )

    ticket_id: Mapped[UUID | None] = mapped_column(nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(nullable=True)

    user_id: Mapped[UUID]
    hours_spent: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=2))
    entry_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    status: Mapped[WorklogStatus] = mapped_column(Enum(WorklogStatus))

    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    __table_args__ = (
        Index(
            "ix_worklogs_user_entry_date", "user_id", "entry_date", postgresql_using="btree"
        ),
        Index("ix_worklogs_user_status", "user_id", "status"),
    )


class TimesheetOrm(Base):
    __tablename__ = "timesheets"

    user_id: Mapped[UUID]
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)

    name: Mapped[str]

    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(nullable=True)

    status: Mapped[TimesheetStatus] = mapped_column(Enum(TimesheetStatus))
    total_hours: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=2))

    approved_hours: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=2))
    pending_hours: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=2))

    worklog_ids: Mapped[list[UUID]] = mapped_column(JSONB)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        # Уникальный ID листа учёта рабочего времени
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_timesheet_user_period"),
        # Индексы
        Index("ix_timesheet_user_period", "user_id", "period_start", "period_end"),
        Index("ix_timesheets_status", "status"),
        Index("ix_timesheets_user_status_period", "user_id", "status", "period_start"),
    )
