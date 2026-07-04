from typing import Any

import logging
from datetime import timedelta
from uuid import UUID

from src.core.settings import settings
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import UnitOfWork, get_or_raise_404
from src.shared.infra.mail import MailSender
from src.shared.utils.time import get_expiration_timestamp

from .constants import INVITATION_EXPIRE_IN_DAYS, INVITATION_SUBJECT, INVITATION_TEXT
from .domain.authz import Subject, can_create_invitation, can_revoke_invitation
from .domain.entities import Invitation, User
from .domain.exceptions import PermissionDeniedError, UnauthorizedError
from .domain.repos import InvitationRepository, TokenStore, UserRepository
from .domain.services import register_new_user
from .domain.vo import Email
from .mappers import map_invitation_to_response
from .schemas import InvitationCreate, InvitationResponse, Tokens, UserCreate
from .security import (
    create_access_token,
    create_refresh_token,
    hash_password_async,
    validate_token,
    verify_password_async,
)

logger = logging.getLogger(__name__)


def create_tokens_for_user(user: User) -> Tokens:
    """
    Выпуск пары токенов access и refresh для пользователя.
    """

    access_token = create_access_token(
        user_id=user.id,
        user_roles=user.roles,
        email=user.email,
        counterparty_id=user.counterparty_id,
    )
    refresh_token = create_refresh_token(user_id=user.id)

    access_token_expires_at = get_expiration_timestamp(
        expires_in=timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
    )

    return Tokens(
        access_token=access_token, refresh_token=refresh_token, expires_at=access_token_expires_at
    )


def build_invitation_mail(invitation: Invitation) -> dict[str, Any]:
    """
    Формирует данные для пригласительного письма.
    """

    invite_url = f"{settings.frontend_url}/auth/invite/accept?token={invitation.token}"
    context = {
        "email": invitation.email,
        "granted_roles": invitation.granted_roles,
        "invite_url": invite_url,
        "expires_in_days": INVITATION_EXPIRE_IN_DAYS,
        "app_name": settings.app.name,
        "support_email": settings.mail.support_email,
    }

    return {
        "to": invitation.email,
        "subject": INVITATION_SUBJECT,
        "plain_text": INVITATION_TEXT,
        "template_name": "email/invitation.html",
        "context": context,
    }


class AuthService:
    def __init__(
            self,
            uow: UnitOfWork,
            user_repo: UserRepository,
            invitation_repo: InvitationRepository,
            token_store: TokenStore,
    ) -> None:
        self.uow = uow
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.token_store = token_store

    async def register(self, token: str, data: UserCreate) -> Tokens:
        """
        Регистрация нового пользователя по приглашению.
        """

        invitation = await self.invitation_repo.get_by_token(token)
        if invitation is None:
            raise NotFoundError(f"Invitation not found by token - {token[1:]}*****")

        existing_user = await self.user_repo.get_by_email(invitation.email)
        if existing_user is not None:
            raise AlreadyExistsError(f"User with email `{invitation.email}` already exists'")

        password_hash = await hash_password_async(data.password)
        user = register_new_user(
            invitation=invitation,
            password_hash=password_hash,
            username=data.username,
            full_name=data.full_name,
        )

        await self.user_repo.create(user)
        await self.invitation_repo.update(invitation)

        tokens = create_tokens_for_user(user)
        await self.uow.commit()

        return tokens

    async def authenticate(self, email: str, password: str) -> Tokens:
        """
        Аутентификация пользователя по его учётным данным.
        """

        user = await self.user_repo.get_by_email(Email(email))
        if user is None:
            raise UnauthorizedError(f"User not found by email - {email}")

        if (
                not await verify_password_async(password, user.password_hash.get_hashed_value()) or
                not user.is_active
        ):
            raise UnauthorizedError("Invalid password or user is not active")

        return create_tokens_for_user(user)

    async def refresh_tokens(self, refresh_token: str) -> Tokens:
        """
        Обновление пары токенов с ротацией.
        """

        payload = validate_token(refresh_token)
        user_id, jti, exp = payload.get("sub"), payload.get("jti"), payload.get("exp", 0)

        if jti is None and user_id is None:
            raise UnauthorizedError("Refresh token is invalid or expired")

        user = await self.user_repo.read(user_id)
        if user is None or not user.is_active:
            await self.token_store.revoke(
                jti, user_id=user_id, exp=exp, reason="user_is_not_active"
            )
            raise UnauthorizedError("User is not active")

        await self.token_store.revoke(jti, user_id=user_id, exp=exp, reason="refresh_tokens")

        return create_tokens_for_user(user)

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """
        Выход с текущего аккаунта.
        """

        try:
            payload = validate_token(access_token)
            jti, exp, user_id = payload.get("jti"), payload.get("exp", 0), payload.get("user_id")

            if jti is not None and exp:
                await self.token_store.revoke(jti, user_id=user_id, exp=exp, reason="user_logout")

        except UnauthorizedError:
            logger.warning("Access token might invalid or expired")

        if refresh_token is not None:
            try:
                payload = validate_token(refresh_token)
                jti, exp, user_id = (
                    payload.get("jti"),
                    payload.get("exp", 0),
                    payload.get("user_id"),
                )
                if jti is not None and exp:
                    await self.token_store.revoke(
                        jti, user_id=user_id, exp=exp, reason="user_logout"
                    )
            except UnauthorizedError:
                logger.warning("Refresh token might invalid or expired")


class InvitationService:
    def __init__(
            self,
            uow: UnitOfWork,
            invitation_repo: InvitationRepository,
            mail_sender: MailSender,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.invitation_repo = invitation_repo
        self.mail_sender = mail_sender
        self.event_publisher = event_publisher

    async def create(
            self, data: InvitationCreate, current_subject: Subject
    ) -> InvitationResponse:
        """
        Создаёт приглашение + публикует событие для отправки на почту.
        """

        permission = can_create_invitation(subject=current_subject)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        invitation = await self.invitation_repo.get_active(Email(data.email), data.granted_roles)

        if invitation is None:
            logger.info("Invitation is not found for email - `%s`, start creating new", data.email)

            invitation = Invitation.create(
                email=Email(data.email),
                invited_by=current_subject.id,
                granted_roles=data.granted_roles,
                counterparty_id=data.counterparty_id,
            )
            await self.invitation_repo.create(invitation)
            await self.uow.commit()
        else:
            invitation.invite()

        for event in invitation.collect_events():
            await self.event_publisher.publish(event)

        return map_invitation_to_response(invitation)

    async def send(self, invitation_id: UUID) -> None:
        """
        Отправка письма на почту.
        """

        invitation = await self.invitation_repo.read(invitation_id)
        if invitation is None:
            logger.warning("Invitation with ID %s not found, skip send mail", invitation_id)
            return

        payload = build_invitation_mail(invitation)
        await self.mail_sender.send(**payload)

        logger.info(
            "Invitation sent: %s -> %s (%s)",
            invitation.invited_by, invitation.email, "; ".join(invitation.granted_roles)
        )

    async def revoke_invitation(self, invitation_id: UUID, current_subject: Subject) -> None:
        """
        Отзыв ошибочно отправленного приглашения.
        """

        invitation = await get_or_raise_404(self.invitation_repo.read, invitation_id, Invitation)

        permission = can_revoke_invitation(subject=current_subject, invitation=invitation)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        await self.invitation_repo.delete(invitation_id)
        await self.uow.commit()
        logger.info("Invitation deleted successfully")
