from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...crm.infra.models import CounterpartyOrm

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import UserRole


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    full_name: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    counterparty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True, unique=False,
    )
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]

    counterparty: Mapped[Optional["CounterpartyOrm"]] = relationship(back_populates="customers")


class InvitationOrm(Base):
    __tablename__ = "invitations"

    email: Mapped[str]
    token: Mapped[str] = mapped_column(unique=True)
    invited_by: Mapped[UUID]
    assigned_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool]
