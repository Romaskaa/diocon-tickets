from datetime import date, datetime
from uuid import UUID

from sqlalchemy import TEXT, Date, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import ProjectRole, ProjectStageStatus, ProjectStatus


class ProjectMembershipOrm(Base):
    __tablename__ = "project_memberships"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    user_id: Mapped[UUID]
    project_role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole))
    created_by: Mapped[UUID]

    project: Mapped["ProjectOrm"] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_membership"),
        Index("ix_project_memberships_project_role", "project_id", "project_role"),
        Index("ix_project_memberships_user", "user_id"),
    )


class ProjectStageOrm(Base):
    __tablename__ = "project_stages"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    name: Mapped[str]
    order: Mapped[int]

    status: Mapped[ProjectStageStatus] = mapped_column(Enum(ProjectStageStatus))

    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_id: Mapped[UUID | None] = mapped_column(nullable=True)

    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    completion_criteria: Mapped[list[str]] = mapped_column(JSONB)

    project: Mapped["ProjectOrm"] = relationship(back_populates="stages")

    __table_args__ = (
        UniqueConstraint("project_id", "order", name="uq_project_stage_order"),
        Index("ix_project_stages_project_order", "project_id", "order"),
        Index("ix_project_stages_status", "status"),
        Index("ix_project_stages_responsible", "responsible_id"),
    )


class ProjectOrm(Base):
    __tablename__ = "projects"

    name: Mapped[str]
    key: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    counterparty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True
    )
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus))
    owner_id: Mapped[UUID]
    created_by: Mapped[UUID]

    current_stage_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_stages.id"), nullable=True
    )
    stages: Mapped[list["ProjectStageOrm"]] = relationship(
        back_populates="project", lazy="selectin", uselist=True, cascade="all, delete-orphan"
    )

    memberships: Mapped[list["ProjectMembershipOrm"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
        Index("ix_projects_counterparty", "counterparty_id"),
        Index("ix_projects_key", "key"),
    )
