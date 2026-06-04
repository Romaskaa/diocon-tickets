# Тесты для доменной сущности User

import uuid

import pytest
from pydantic import SecretStr

from src.iam.domain.entities import User
from src.iam.domain.services import create_customer, create_support
from src.iam.domain.vo import FullName, Username, UserRole
from src.shared.domain.exceptions import InvariantViolationError


@pytest.fixture
def valid_email():
    return "test@example.com"


@pytest.fixture
def valid_password_hash():
    return "pbkdf2:sha256:600000$salt$hashvalue"


@pytest.fixture
def counterparty_id():
    return uuid.uuid4()


def test_create_customer_minimal(valid_email, valid_password_hash, counterparty_id):
    user = create_customer(
        email=valid_email,
        password_hash=valid_password_hash,
        counterparty_id=counterparty_id,
    )

    assert isinstance(user, User)
    assert str(user.email) == valid_email
    assert user.role == UserRole.CUSTOMER
    assert user.counterparty_id == counterparty_id
    assert user.is_active is True
    assert user.username is None
    assert user.full_name is None


def test_create_customer_with_full_data(valid_email, valid_password_hash, counterparty_id):
    user = create_customer(
        email=valid_email,
        password_hash=valid_password_hash,
        counterparty_id=counterparty_id,
        username="client_anna",
        full_name="Анна Петрова",
        user_role=UserRole.CUSTOMER_ADMIN,
    )

    assert isinstance(user.username, Username)
    assert str(user.username) == "client_anna"
    assert isinstance(user.full_name, FullName)
    assert str(user.full_name) == "Анна Петрова"
    assert user.role == UserRole.CUSTOMER_ADMIN
    assert user.counterparty_id == counterparty_id


def test_create_customer_without_counterparty_raises_error(valid_email, valid_password_hash):
    with pytest.raises(InvariantViolationError) as exc:
        create_customer(
            email=valid_email,
            password_hash=valid_password_hash,
            counterparty_id=None,
        )
    assert "Counterparty must be specified" in str(exc.value)


def test_create_support_minimal(valid_email, valid_password_hash):
    user = create_support(
        email=valid_email,
        password_hash=valid_password_hash,
    )

    assert isinstance(user, User)
    assert str(user.email) == valid_email
    assert user.role == UserRole.SUPPORT_AGENT
    assert user.counterparty_id is None          # для support это нормально
    assert user.is_active is True
    assert user.username is None
    assert user.full_name is None


def test_create_support_manager(valid_email, valid_password_hash):
    user = create_support(
        email=valid_email,
        password_hash=valid_password_hash,
        username="support-lead",
        full_name="Мария Иванова",
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert user.role == UserRole.SUPPORT_MANAGER
    assert isinstance(user.username, Username)
    assert user.username == "support-lead"
    assert isinstance(user.full_name, FullName)
    assert str(user.full_name) == "Мария Иванова"
    assert user.counterparty_id is None


def test_direct_creation_agent_without_counterparty(valid_email, valid_password_hash):
    user = User(
        email=valid_email,
        password_hash=SecretStr(valid_password_hash),
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )
    assert user.role == UserRole.SUPPORT_AGENT
    assert user.counterparty_id is None


def test_direct_creation_customer_without_counterparty_raises(valid_email, valid_password_hash):
    with pytest.raises(InvariantViolationError):
        User(
            email=valid_email,
            password_hash=SecretStr(valid_password_hash),
            role=UserRole.CUSTOMER,
            counterparty_id=None,
        )


def test_direct_creation_customer_admin_without_counterparty_raises(
        valid_email, valid_password_hash
):
    with pytest.raises(InvariantViolationError):
        User(
            email=valid_email,
            password_hash=SecretStr(valid_password_hash),
            role=UserRole.CUSTOMER_ADMIN,
            counterparty_id=None,
        )


def test_username_and_full_name_optional(valid_email, valid_password_hash):
    user = create_support(
        email=valid_email,
        password_hash=valid_password_hash,
        username=None,
        full_name=None,
    )
    assert user.username is None
    assert user.full_name is None


def test_is_active_default_true(valid_email, valid_password_hash):
    user = create_customer(
        email=valid_email,
        password_hash=valid_password_hash,
        counterparty_id=uuid.uuid4(),
    )
    assert user.is_active is True
