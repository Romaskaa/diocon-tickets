from datetime import date, datetime
from uuid import UUID

from sqlalchemy import TEXT, Date, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import ProjectRole, ProjectStageStatus, ProjectStatus


class ProjectMemberOrm(Base):
    __tablename__ = "project_members"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    user_id: Mapped[UUID]
    project_roles: Mapped[list[ProjectRole]] = mapped_column(JSONB)
    created_by: Mapped[UUID]

    project: Mapped["ProjectOrm"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        Index("ix_project_members_project_role", "project_id", "project_role"),
        Index("ix_project_members_user", "user_id"),
    )


class ProjectStageOrm(Base):
    __tablename__ = "project_stages"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    name: Mapped[str]
    execution_order: Mapped[int]

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
        Index("ix_project_stages_project_order", "project_id", "execution_order"),
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

    stages: Mapped[list["ProjectStageOrm"]] = relationship(
        back_populates="project", lazy="selectin", uselist=True, cascade="all, delete-orphan"
    )

    members: Mapped[list["ProjectMemberOrm"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
        Index("ix_projects_counterparty", "counterparty_id"),
        Index("ix_projects_key", "key"),
    )
