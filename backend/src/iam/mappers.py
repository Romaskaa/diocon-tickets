# Модуль для маппинга доменных моделей в API схемы

from .domain.entities import Invitation, User
from .schemas import InvitationResponse, UserResponse


def map_user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email=user.email,
        username=f"{user.username}",
        full_name=f"{user.full_name}",
        avatar_url=user.avatar_url,
        role=user.role,
        counterparty_id=user.counterparty_id,
        is_active=user.is_active,
    )


def map_invitation_to_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        created_at=invitation.created_at,
        invited_by=invitation.invited_by,
        email=invitation.email,
        assigned_role=invitation.assigned_role,
        counterparty_id=invitation.counterparty_id,
        expires_at=invitation.expires_at,
        used_at=invitation.used_at,
        is_used=invitation.is_used,
    )
