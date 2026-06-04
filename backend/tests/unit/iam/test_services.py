from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from faker import Faker
from freezegun import freeze_time

from src.iam.domain.exceptions import InvitationExpiredError
from src.iam.domain.services import (
    create_account_manager,
    create_admin,
    create_customer,
    create_finance,
    create_support,
    invite_customer,
    invite_support,
)
from src.iam.domain.vo import UserRole
from src.iam.schemas import Tokens, UserCreateForm
from src.iam.security import hash_password, validate_token
from src.iam.services import AuthService, InvitationService, create_tokens_for_user
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.utils.time import current_datetime

fake = Faker()


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_auth_service(mock_session, mock_user_repo, mock_invitation_repo, mock_token_blacklist):
    return AuthService(
        session=mock_session,
        user_repo=mock_user_repo,
        invitation_repo=mock_invitation_repo,
        blacklist=mock_token_blacklist,
    )


@pytest.fixture
def sample_counterparty_id():
    return uuid4()


@pytest.fixture
def sample_password():
    return "StrongPass123!"


@pytest.fixture
def mock_invitation_for_customer(sample_counterparty_id):
    return invite_customer(
        invited_by=uuid4(),
        email="customer@emample.com",
        assigned_role=UserRole.CUSTOMER,
        counterparty_id=sample_counterparty_id,
    )


@pytest.fixture
def sample_form_data(sample_password):
    return UserCreateForm(
        username="customer1", full_name="Иванов Иван Иванович", password=sample_password,
    )


@pytest.fixture
def mock_mail_sender():
    return AsyncMock()


@pytest.fixture
def mock_invitation_service(mock_session, mock_invitation_repo, mock_mail_sender):
    return InvitationService(
        session=mock_session,
        repository=mock_invitation_repo,
        mail_sender=mock_mail_sender,
    )


def generate_password_hash():
    return hash_password(
        fake.password(
            length=12,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )
    )


def make_customer():
    return create_customer(
        email=fake.email(),
        password_hash=generate_password_hash(),
        username=fake.user_name(),
        full_name=fake.name(),
        counterparty_id=uuid4(),
        user_role=UserRole.CUSTOMER_ADMIN,
    )


def make_support():
    return create_support(
        email=fake.email(),
        password_hash=generate_password_hash(),
        full_name=fake.name(),
        user_role=UserRole.SUPPORT_MANAGER,
    )


def make_admin():
    return create_admin(email=fake.email(), password_hash=generate_password_hash())


def make_account_manager():
    return create_account_manager(
        email=fake.email(), password_hash=generate_password_hash(), full_name=fake.name(),
    )


def make_finance():
    return create_finance(
        email=fake.email(), password_hash=generate_password_hash(), full_name=fake.name()
    )


class TestCreateTokensForUser:
    """Тесты для метода create_tokens_for_user"""

    @pytest.mark.parametrize(
        "user", [
            make_support(), make_admin(), make_customer(), make_account_manager(), make_finance()
        ]
    )
    def test_create_tokens_for_user(self, user):
        # 1. Получение пары токенов
        tokens = create_tokens_for_user(user)

        assert isinstance(tokens, Tokens)

        # 2. Валидация токенов для проверки claims
        access_payload = validate_token(tokens.access_token)
        refresh_payload = validate_token(tokens.refresh_token)

        # 3. Проверка access токена
        assert access_payload["sub"] == f"{user.id}"
        assert access_payload["type"] == "access"
        assert access_payload["email"] == user.email
        assert access_payload["role"] == user.role

        if user.counterparty_id is not None:
            assert "counterparty_id" in access_payload
            assert access_payload["counterparty_id"] == f"{user.counterparty_id}"

        # 4. Проверка refresh токена
        assert refresh_payload["sub"] == f"{user.id}"
        assert refresh_payload["type"] == "refresh"


class TestAuthServiceRegister:
    """Тесты для методы register (регистрация по приглашению)"""

    @pytest.mark.asyncio
    async def test_register_success_customer(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_user_repo,
            mock_invitation_for_customer,
            sample_form_data,
    ):
        # 1. Сохранения приглашения
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Регистрация по созданному приглашению
        await mock_auth_service.register(invitation.token, sample_form_data)

        # 3. Поиск зарегистрированного пользователя по email
        existing_user = await mock_user_repo.get_by_email(invitation.email)

        assert existing_user is not None
        assert existing_user.email == invitation.email

    @pytest.mark.asyncio
    async def test_register_raises_invitation_not_found(self, mock_auth_service, sample_form_data):
        with pytest.raises(NotFoundError, match="Invitation not found"):
            await mock_auth_service.register("wrong-token", sample_form_data)

    @pytest.mark.asyncio
    async def test_register_raises_invitation_expired(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_invitation_for_customer,
            sample_form_data,
    ):

        # 1. Сохранения приглашения
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Прокрутка времени на 20 дней вперёд, чтобы приглашение истекло
        with (
            freeze_time(current_datetime() + timedelta(days=20)),
            pytest.raises(InvitationExpiredError)
        ):
            await mock_auth_service.register(invitation.token, sample_form_data)

    @pytest.mark.asyncio
    async def test_register_user_already_exists(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_user_repo,
            mock_invitation_for_customer,
            sample_form_data,
            sample_counterparty_id,
    ):

        # 1. Создание и сохранение пользователя
        password = "StrongPass123!"
        user = create_customer(
            email="customer@emample.com",
            password_hash=hash_password(password),
            counterparty_id=sample_counterparty_id,
        )
        await mock_user_repo.create(user)

        # 2. Создание и сохранение приглашения (чтобы исключить ошибки с приглашением)
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Попытка регистрации уже существующего пользователя
        with pytest.raises(AlreadyExistsError):
            await mock_auth_service.register(invitation.token, sample_form_data)


class TestAuthServiceAuthenticate:
    """Тесты для метода authenticate"""

    @pytest.mark.asyncio
    async def test_authenticate_success(
            self,
            sample_counterparty_id,
            sample_password,
            mock_user_repo,
            mock_auth_service,
    ):

        # 1. Сохранение пользователя на прямую в БД
        user = create_customer(
            email="customer@emample.com",
            password_hash=hash_password(sample_password),
            counterparty_id=sample_counterparty_id,
        )
        await mock_user_repo.create(user)

        # 2. Аутентификация пользователя
        tokens = await mock_auth_service.authenticate(user.email, sample_password)

        assert isinstance(tokens, Tokens)


class TestInvitationServiceSendInvitation:
    """
    Тестирование отправки приглашения
    """

    @pytest.mark.asyncio
    async def test_send_invitation_support_new(
            self, mock_invitation_service, mock_invitation_repo, mock_session, mock_mail_sender
    ):
        # 1. Создание и отправка приглашения
        invited_by = uuid4()
        email = fake.email()
        assigned_role = UserRole.SUPPORT_AGENT

        invitation = await mock_invitation_service.send_invitation(
            invited_by=invited_by, email=email, assigned_role=assigned_role
        )

        # 2. Проверка успешного создания и записи приглашения
        created_invitation = await mock_invitation_repo.read(invitation.id)

        mock_session.commit.assert_awaited_once()
        assert created_invitation is not None
        assert created_invitation.invited_by == invited_by
        assert created_invitation.assigned_role == assigned_role
        assert created_invitation.email == email

        # 3. Проверка отправки письма
        mock_mail_sender.send.assert_awaited_once()

        send_call_kwargs = mock_mail_sender.send.call_args[1]

        assert send_call_kwargs["to"] == email
        assert created_invitation.token in send_call_kwargs["context"]["invite_url"]

        assert invitation == created_invitation

    @pytest.mark.asyncio
    async def test_send_invitation_customer_new(
            self, mock_invitation_service, mock_invitation_repo, mock_session, mock_mail_sender
    ):
        # 1. Создание и отправка приглашения
        invited_by = uuid4()
        email = fake.email()
        assigned_role = UserRole.CUSTOMER
        counterparty_id = uuid4()

        invitation = await mock_invitation_service.send_invitation(
            invited_by=invited_by,
            email=email,
            assigned_role=assigned_role,
            counterparty_id=counterparty_id,
        )

        # 2. Проверка успешного создания и записи приглашения
        created_invitation = await mock_invitation_repo.read(invitation.id)

        mock_session.commit.assert_awaited_once()
        assert created_invitation is not None
        assert created_invitation.invited_by == invited_by
        assert created_invitation.assigned_role == assigned_role
        assert created_invitation.email == email
        assert created_invitation.counterparty_id == counterparty_id

        # 3. Проверка отправки письма
        mock_mail_sender.send.assert_awaited_once()

        send_call_kwargs = mock_mail_sender.send.call_args[1]

        assert send_call_kwargs["to"] == email
        assert created_invitation.token in send_call_kwargs["context"]["invite_url"]

        assert invitation == created_invitation

    @pytest.mark.asyncio
    async def test_send_invitation_already_exists(
            self, mock_invitation_service, mock_invitation_repo, mock_session, mock_mail_sender
    ):
        # 1. Создание и сохранение приглашения
        invited_by = uuid4()
        email = fake.email()
        assigned_role = UserRole.SUPPORT_AGENT

        invitation = invite_support(
            invited_by=invited_by, email=email, assigned_role=assigned_role
        )
        await mock_invitation_repo.create(invitation)

        # 2. Попытка отправки приглашения
        sent_invitation = await mock_invitation_service.send_invitation(
            invited_by=invited_by, email=email, assigned_role=assigned_role
        )

        mock_session.commit.assert_not_called()
        mock_mail_sender.send.assert_awaited_once()

        send_call_kwargs = mock_mail_sender.send.call_args[1]

        assert send_call_kwargs["to"] == email
        assert sent_invitation.token in send_call_kwargs["context"]["invite_url"]

        assert invitation == sent_invitation

    @pytest.mark.asyncio
    async def test_send_invitation_raises_invalid_params(
            self, mock_invitation_service
    ):
        invited_by = uuid4()
        email = fake.email()

        with pytest.raises(ValueError, match="Invalid invite params"):
            await mock_invitation_service.send_invitation(
                invited_by=invited_by,
                email=email,
                assigned_role=UserRole.CUSTOMER,
            )


class TestInvitationServiceRevokeInvitation:
    """
    Тестирование отзыва приглашения
    """

    @pytest.mark.asyncio
    async def test_revoke_invitation_success(
            self, mock_invitation_service, mock_invitation_repo, mock_session
    ):
        invitation = invite_support(
            invited_by=uuid4(), email=fake.email(), assigned_role=UserRole.SUPPORT_AGENT
        )
        await mock_invitation_repo.create(invitation)

        await mock_invitation_service.revoke_invitation(invitation.id)

        mock_session.commit.assert_awaited_once()

        existing_invitation = await mock_invitation_repo.read(invitation.id)

        assert existing_invitation is None

    @pytest.mark.asyncio
    async def test_revoke_invitation_raises_not_found(self, mock_invitation_service):
        with pytest.raises(NotFoundError):
            await mock_invitation_service.revoke_invitation(uuid4())
