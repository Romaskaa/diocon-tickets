import uuid
from datetime import datetime, timedelta

import pytest

from src.iam.domain.entities import Invitation
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime


@pytest.fixture
def future_expires_at():
    return current_datetime() + timedelta(days=7)


@pytest.fixture
def past_expires_at():
    return current_datetime() - timedelta(hours=1)


@pytest.fixture
def admin_id():
    return uuid.uuid4()


@pytest.fixture
def counterparty_id():
    return uuid.uuid4()


def test_can_create_customer_invitation(
        admin_id: uuid.UUID, counterparty_id: uuid.UUID, future_expires_at: datetime
):
    invitation = Invitation(
        email="client@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.CUSTOMER,
        counterparty_id=counterparty_id,
        expires_at=future_expires_at,
    )

    assert invitation.email == "client@example.com"
    assert invitation.assigned_role == UserRole.CUSTOMER
    assert invitation.counterparty_id == counterparty_id
    assert invitation.is_used is False
    assert invitation.used_at is None
    assert invitation.is_valid is True


def test_can_create_support_invitation_without_counterparty(
        admin_id: uuid.UUID, future_expires_at: datetime
):
    invitation = Invitation(
        email="agent@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
        expires_at=future_expires_at,
    )

    assert invitation.counterparty_id is None
    assert invitation.is_valid is True


def test_customer_invitation_without_counterparty_raises_error(
        admin_id: uuid.UUID, future_expires_at: datetime
):
    with pytest.raises(InvariantViolationError) as exc:
        Invitation(
            email="client@example.com",
            invited_by=admin_id,
            assigned_role=UserRole.CUSTOMER,
            counterparty_id=None,
            expires_at=future_expires_at,
        )
    assert "must specify a counterparty ID" in str(exc.value)


def test_customer_admin_invitation_without_counterparty_raises_error(
        admin_id: uuid.UUID, future_expires_at: datetime
):
    with pytest.raises(InvariantViolationError):
        Invitation(
            email="admin@example.com",
            invited_by=admin_id,
            assigned_role=UserRole.CUSTOMER_ADMIN,
            counterparty_id=None,
            expires_at=future_expires_at,
        )


def test_support_invitation_with_counterparty_raises_error(
        admin_id: uuid.UUID, counterparty_id: uuid.UUID, future_expires_at: datetime
):
    with pytest.raises(InvariantViolationError) as exc:
        Invitation(
            email="agent@example.com",
            invited_by=admin_id,
            assigned_role=UserRole.SUPPORT_AGENT,
            counterparty_id=counterparty_id,
            expires_at=future_expires_at,
        )
    assert "does not need to be specified" in str(exc.value)


def test_is_valid_true_when_not_used_and_not_expired(
        admin_id: uuid.UUID, future_expires_at: datetime
):
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=future_expires_at,
    )
    assert invitation.is_valid is True


def test_is_valid_false_when_used(admin_id: uuid.UUID, future_expires_at: datetime):
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=future_expires_at,
    )
    invitation.mark_as_used()
    assert invitation.is_valid is False


def test_is_valid_false_when_expired(admin_id: uuid.UUID, past_expires_at: datetime):
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=past_expires_at,
    )
    assert invitation.is_valid is False


def test_is_valid_false_when_used_and_expired(admin_id: uuid.UUID, past_expires_at: datetime):
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=past_expires_at,
    )
    invitation.mark_as_used()
    assert invitation.is_valid is False


def test_mark_as_used_sets_fields_correctly(admin_id: uuid.UUID, future_expires_at: datetime):
    before = current_datetime()
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.ADMIN,
        expires_at=future_expires_at,
    )

    invitation.mark_as_used()

    after = current_datetime()

    assert invitation.is_used is True
    assert invitation.used_at is not None
    assert before <= invitation.used_at <= after
    assert invitation.is_valid is False


def test_token_generated_by_default_factory(admin_id: uuid.UUID, future_expires_at: datetime):
    first_invitation = Invitation(
        email="a@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=future_expires_at,
    )
    second_invitation = Invitation(
        email="b@example.com",
        invited_by=admin_id,
        assigned_role=UserRole.SUPPORT_AGENT,
        expires_at=future_expires_at,
    )

    min_token_length = 20

    assert first_invitation.token != second_invitation.token
    assert len(first_invitation.token) >= min_token_length


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.SUPPORT_MANAGER])
def test_admin_and_manager_can_have_no_counterparty(
        role: UserRole, admin_id: uuid.UUID, future_expires_at: datetime
):
    invitation = Invitation(
        email="test@example.com",
        invited_by=admin_id,
        assigned_role=role,
        counterparty_id=None,
        expires_at=future_expires_at,
    )
    assert invitation.counterparty_id is None
