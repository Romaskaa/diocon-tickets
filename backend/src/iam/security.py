from typing import Any

import logging
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext

from ..core.settings import settings
from ..shared.utils.time import current_datetime
from .domain.exceptions import UnauthorizedError
from .domain.vo import UserRole

# Хеширование паролей
MEMORY_COST = 100  # Размер выделяемой памяти в MB
TIME_COST = 2
PARALLELISM = 2
SALT_SIZE = 16
ROUNDS = 14  # Количество раундов для хеширования

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=MEMORY_COST,
    argon2__time_cost=TIME_COST,
    argon2__parallelism=PARALLELISM,
    argon2__salt_size=SALT_SIZE,
    bcrypt__rounds=ROUNDS,
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """Создание хеша для пароля"""

    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Сверяет ожидаемый пароль с хэшем пароля"""

    return pwd_context.verify(plain_password, password_hash)


def create_access_token(
        user_id: UUID,
        email: str,
        user_role: UserRole,
        counterparty_id: UUID | None = None,
) -> str:
    """Выпуск access токена"""

    now = current_datetime()
    expires_at = now + timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
    payload = {
        "sub": f"{user_id}",
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "type": "access",
        "jti": f"{uuid4()}",
        "email": email,
        "role": user_role.value,
    }
    if counterparty_id is not None:
        payload["counterparty_id"] = f"{counterparty_id}"

    return jwt.encode(payload=payload, key=settings.secret_key, algorithm=settings.jwt.algorithm)


def create_refresh_token(user_id: UUID) -> str:
    """Выпуск refresh токена"""

    now = current_datetime()
    expires_at = now + timedelta(days=settings.jwt.refresh_token_expires_in_days)
    payload = {
        "sub": f"{user_id}",
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "type": "refresh",
        "jti": f"{uuid4()}",
    }
    return jwt.encode(payload=payload, key=settings.secret_key, algorithm=settings.jwt.algorithm)


def validate_token(token: str) -> dict[str, Any]:
    """Декодирование и проверка подписи токена"""

    try:
        return jwt.decode(
            token,
            key=settings.secret_key,
            algorithms=[settings.jwt.algorithm],
            options={"verify_aud": False}
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token signature expired!") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token!") from None
