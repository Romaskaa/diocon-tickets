from fastapi import status

from ...shared.domain.exceptions import AppError


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    public_message = "Недостаточно прав"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    public_message = "Требуется авторизация"


class InvitationExpiredError(AppError):
    status_code = status.HTTP_410_GONE
    error_code = "INVITATION_EXPIRED"
    public_message = "Приглашение было использовано или его срок действия истёк"
