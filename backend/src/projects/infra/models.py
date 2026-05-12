from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import ProjectRole, ProjectStatus


class MembershipOrm(Base):
    __tablename__ = "project_memberships"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    user_id: Mapped[UUID]
    project_role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[UUID]

    project: Mapped["ProjectOrm"] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_membership"),
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

    memberships: Mapped[list["MembershipOrm"]] = relationship(back_populates="project")

    __table_args__ = (
        Index("ix_project_key", "key"),
    )
