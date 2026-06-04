from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.notifications.channels import NotificationChannel
from src.notifications.domain.entities import UserPreference
from src.notifications.domain.vo import ChannelType, NotificationType
from src.notifications.resolvers import ChannelResolver


@pytest.fixture
def email_channel():
    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.EMAIL
    return channel


@pytest.fixture
def in_app_channel():
    channel = AsyncMock(spec=NotificationChannel)
    channel.channel_type = ChannelType.IN_APP
    return channel


@pytest.fixture
def channel_resolver(mock_preference_repo, email_channel, in_app_channel):
    return ChannelResolver(mock_preference_repo, email_channel, in_app_channel)


class TestChannelResolver:
    """
    Тесты для определения каналов уведомлений пользователя
    """

    @pytest.mark.asyncio
    async def test_resolve_no_preference_returns_all_channels(
            self, channel_resolver, email_channel, in_app_channel
    ):
        """
        Если нет настройки, то доступны все каналы
        """

        user_id = uuid4()
        notification_type = NotificationType.TICKET_ASSIGNED

        channels = await channel_resolver.resolve(user_id, notification_type)
        excepted_channels_length = 2

        assert len(channels) == excepted_channels_length
        assert email_channel in channels
        assert in_app_channel in channels

    @pytest.mark.asyncio
    async def test_resolve_with_preference_enabled_channels(
            self, mock_preference_repo, channel_resolver, email_channel, in_app_channel
    ):
        """
        Должны быть доступны только разрешённые каналы уведомлений
        """

        user_id = uuid4()
        notification_type = NotificationType.TICKET_CREATED

        preference = UserPreference(user_id=user_id, notification_type=notification_type)
        preference.disable_channel(ChannelType.IN_APP)
        await mock_preference_repo.create(preference)

        channels = await channel_resolver.resolve(user_id, notification_type)
        excepted_channels_length = 1

        assert len(channels) == excepted_channels_length
        assert email_channel in channels
        assert in_app_channel not in channels

    @pytest.mark.asyncio
    async def test_resolve_all_channels_disabled_returns_empty_list(
            self, mock_preference_repo, channel_resolver
    ):
        """
        Если все каналы отключены пользователем, то нет уведомлений
        """

        user_id = uuid4()
        notification_type = NotificationType.TICKET_CREATED

        preference = UserPreference(user_id=user_id, notification_type=notification_type)
        preference.disable_channel(ChannelType.IN_APP)
        preference.disable_channel(ChannelType.EMAIL)
        await mock_preference_repo.create(preference)

        channels = await channel_resolver.resolve(user_id, notification_type)

        assert len(channels) == 0

    @pytest.mark.asyncio
    async def test_resolve_when_preference_muted_returns_empty_list(
            self, channel_resolver, mock_preference_repo
    ):
        """
        В настройках каналы заглушены - то пустой список
        """

        user_id = uuid4()
        notification_type = NotificationType.TICKET_STATUS_CHANGED

        preference = UserPreference(user_id=user_id, notification_type=notification_type)
        preference.mute(timedelta(hours=1))
        await mock_preference_repo.create(preference)

        channels = await channel_resolver.resolve(user_id, notification_type)

        assert len(channels) == 0
