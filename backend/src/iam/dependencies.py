from typing import Annotated

from fastapi import Depends, Query, WebSocket, status
from fastapi.security import OAuth2PasswordBearer

from ..core.redis import redis_client
from ..core.settings import settings
from ..shared.dependencies import SessionDep
from ..shared.infra.mail import SmtpMailSender
from .domain.exceptions import PermissionDeniedError, UnauthorizedError
from .domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from .domain.vo import UserRole
from .infra.blacklist import RedisTokenBlacklist
from .infra.repos import SqlInvitationRepository, SqlUserRepository
from .schemas import CurrentUser
from .security import validate_token
from .services import AuthService, InvitationService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


def get_user_repo(session: SessionDep) -> UserRepository:
    return SqlUserRepository(session)


def get_token_blacklist() -> TokenBlacklist:
    return RedisTokenBlacklist(redis_client)


def get_invitation_repo(session: SessionDep) -> InvitationRepository:
    return SqlInvitationRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]


def get_auth_service(
        session: SessionDep,
        user_repo: Annotated[UserRepository, Depends(get_user_repo)],
        invitation_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
        blacklist: Annotated[TokenBlacklist, Depends(get_token_blacklist)],
) -> AuthService:
    return AuthService(
        session, user_repo=user_repo, invitation_repo=invitation_repo, blacklist=blacklist
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_mail_sender() -> SmtpMailSender:
    return SmtpMailSender(
        smtp_host=settings.mail.smtp_host,
        smtp_port=settings.mail.smtp_port,
        use_tls=settings.mail.smtp_use_tls,
    )


def get_invitation_service(
        session: SessionDep,
        repository: Annotated[InvitationRepository, Depends(get_invitation_repo)],
        mail_sender: Annotated[SmtpMailSender, Depends(get_mail_sender)],
) -> InvitationService:
    return InvitationService(session, repository=repository, mail_sender=mail_sender)


InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]


async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        blacklist: Annotated[TokenBlacklist, Depends(get_token_blacklist)],
) -> CurrentUser:
    """Получение текущего пользователя"""

    # 1. Валидация токена
    payload = validate_token(token)
    jti, user_id = payload.get("jti"), payload.get("sub")

    # 2. Проверка на наличие в чёрных списках
    if jti is None or await blacklist.is_revoked(jti):
        raise UnauthorizedError("Token has been revoked or missing jti")
    if user_id is None:
        raise UnauthorizedError("Invalid token: missing sub claim")

    return CurrentUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        counterparty_id=payload.get("counterparty_id"),
    )


def require_role(*allowed_roles: UserRole):
    """Зависимость для ограничения доступа по ролям"""

    def checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError("Insufficient permissions")
        return current_user

    return checker


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_current_support_user(current_user: CurrentUserDep) -> CurrentUser:
    """Зависимость для эндпоинтов, доступных только сотрудникам поддержки"""

    if current_user.role not in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        raise PermissionDeniedError("Access restricted to support staff only")

    return current_user


def get_current_customer_admin(current_user: CurrentUserDep) -> CurrentUser:
    """Зависимость для эндпоинтов, доступных только админов клиента и выше"""

    if current_user.role not in {
        UserRole.CUSTOMER_ADMIN, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
    }:
        raise PermissionDeniedError("Access restricted to customer admin or higher")

    return current_user


CurrentSupportUserDep = Annotated[CurrentUser, Depends(get_current_support_user)]
CurrentCustomerAdminDep = Annotated[CurrentUser, Depends(get_current_customer_admin)]


async def get_current_user_from_ws(
        websocket: WebSocket,
        token: str | None = Query(None, description="Access токен"),
        blacklist: TokenBlacklist = Depends(get_token_blacklist),
) -> CurrentUser | None:
    # 1. Получение access токена из текущего соединения
    token = token or websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return None

    # 2. Декодирование токена и проверка нет ли его в черном списке
    payload = validate_token(token)
    jti, user_id = payload.get("jti"), payload.get("sub")
    is_revoked = await blacklist.is_revoked(jti)
    if jti is None or is_revoked or user_id is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token or blacklisted"
        )
        return None

    return CurrentUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        counterparty_id=payload.get("counterparty_id"),
    )
