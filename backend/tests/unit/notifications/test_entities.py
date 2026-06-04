from datetime import timedelta
from uuid import uuid4

import pytest
from freezegun import freeze_time

from src.iam.domain.exceptions import PermissionDeniedError
from src.notifications.domain.entities import Notification, UserPreference
from src.notifications.domain.vo import ChannelType, NotificationType
from src.shared.utils.time import current_datetime


class TestNotification:
    """
    Тесты для сущности уведомления
    """

    def test_mark_as_read(self):

        user_id = uuid4()
        notification = Notification(
            user_id=user_id,
            title="Новое уведомление",
            message="Тестовое сообщение",
            type=NotificationType.TICKET_CREATED,
        )

        original_updated_at = notification.updated_at

        assert notification.read is False

        with freeze_time(current_datetime() + timedelta(seconds=5)):
            notification.mark_as_read(user_id)

        assert notification.read is True
        assert notification.updated_at > original_updated_at

    def test_mark_as_read_does_not_update_if_already_read(self):
        user_id = uuid4()
        notification = Notification(
            user_id=user_id,
            title="Новое уведомление",
            message="Тестовое сообщение",
            type=NotificationType.TICKET_CREATED,
            read=True,
        )

        original_updated_at = notification.updated_at

        with freeze_time(current_datetime() + timedelta(seconds=5)):
            notification.mark_as_read(user_id)

        assert notification.read is True
        assert notification.updated_at == original_updated_at

    def test_mark_as_read_does_not_receiver(self):
        notification = Notification(
            user_id=uuid4(),
            title="Новое уведомление",
            message="Тестовое сообщение",
            type=NotificationType.TICKET_CREATED,
        )

        with pytest.raises(PermissionDeniedError, match="You can only read your notifications"):
            notification.mark_as_read(read_by=uuid4())


class TestUserPreference:
    """
    Тесты для настроек пользователя
    """

    @pytest.fixture
    def user_preference(self):
        return UserPreference(user_id=uuid4(), notification_type=NotificationType.SYSTEM)

    @pytest.mark.parametrize(
        ("channel", "expected"),
        [
            (ChannelType.EMAIL, True),
            (ChannelType.IN_APP, True),
        ],
    )
    def test_is_enabled_for_channel_returns_correct_flag(self, user_preference, channel, expected):
        assert user_preference.is_enabled_for_channel(channel) == expected

    def test_mute_sets_muted_until_correctly(self, user_preference):
        duration = timedelta(hours=1)

        with freeze_time(current_datetime()):
            user_preference.mute(duration)

            assert user_preference.muted_until is not None
            assert user_preference.muted_until == current_datetime() + duration
            assert user_preference.is_muted is True

    def test_mute_to_past_time_failure(self, user_preference):
        duration = -timedelta(hours=1)

        with pytest.raises(ValueError, match="Mute until must be in the future"):
            user_preference.mute(duration)

    def test_unmute_make_muted_until_none(self, user_preference):
        duration = timedelta(hours=1)
        user_preference.mute(duration)

        assert user_preference.muted_until is not None

        user_preference.unmute()

        assert user_preference.muted_until is None
        assert user_preference.is_muted is False

    @pytest.mark.parametrize(
        ("channel", "expected"),
        [
            (ChannelType.EMAIL, False),
            (ChannelType.IN_APP, False),
        ],
    )
    def test_is_enabled_for_channel_returns_false_when_muted(
            self, user_preference, channel, expected
    ):
        duration = timedelta(hours=1)
        user_preference.mute(duration)

        assert user_preference.is_enabled_for_channel(channel) is expected

    @pytest.mark.parametrize(
        ("channel", "expected"),
        [
            (ChannelType.EMAIL, True),
            (ChannelType.IN_APP, True),
        ],
    )
    def test_is_enabled_for_channel_restores_after_mute_expires(
            self, user_preference, channel, expected
    ):
        duration = timedelta(hours=1)
        user_preference.mute(duration)

        with freeze_time(current_datetime() + duration):
            assert user_preference.is_enabled_for_channel(channel) is expected

    def test_disable_channel_updates_flag_and_updated_at(self, user_preference):
        original_updated_at = user_preference.updated_at

        with freeze_time(current_datetime() + timedelta(seconds=1)):
            user_preference.disable_channel(ChannelType.EMAIL)

        assert user_preference.is_enabled_for_channel(ChannelType.EMAIL) is False
        assert user_preference.is_enabled_for_channel(ChannelType.IN_APP) is True
        assert user_preference.updated_at > original_updated_at

    def test_enable_channel_updates_flag_and_updated_at(self, user_preference):
        user_preference.disable_channel(ChannelType.IN_APP)
        original_updated_at = user_preference.updated_at

        with freeze_time(current_datetime() + timedelta(seconds=1)):
            user_preference.enable_channel(ChannelType.IN_APP)

        assert user_preference.is_enabled_for_channel(ChannelType.IN_APP) is True
        assert user_preference.is_enabled_for_channel(ChannelType.EMAIL) is True
        assert user_preference.updated_at > original_updated_at
