from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...media.infra.models import AttachmentOrm

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ...tickets.domain.vo import Priority
from ..domain.vo import TaskStatus


class TaskOrm(Base):
    __tablename__ = "tasks"

    ticket_id: Mapped[UUID | None] = mapped_column(nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(nullable=True)

    number: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus))
    priority: Mapped[Priority] = mapped_column(Enum(Priority))
    story_points: Mapped[int | None] = mapped_column(nullable=True)

    assignee_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewer_id: Mapped[UUID | None] = mapped_column(nullable=True)

    estimated_hours: Mapped[float | None] = mapped_column(nullable=True)
    actual_hours: Mapped[float] = mapped_column(default=0.0)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[UUID]

    tags: Mapped[list[dict[str, str]]] = mapped_column(JSONB)

    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='task', "
            "foreign(AttachmentOrm.owner_id)==TaskOrm.id)"
        ),
        lazy="selectin",
        viewonly=True,
    )


class TaskSequence(Base):
    __tablename__ = "tasks_sequences"

    project_id: Mapped[UUID | None] = mapped_column(nullable=True)
    ticket_id: Mapped[UUID | None] = mapped_column(nullable=True)
    last_number: Mapped[int]

    __table_args__ = (
        UniqueConstraint(
            "project_id", "ticket_id", name="uq_task_sequences", postgresql_nulls_not_distinct=True
        ),
    )
