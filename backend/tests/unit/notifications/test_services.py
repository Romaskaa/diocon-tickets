import logging
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.channels import NotificationChannel
from src.notifications.domain.entities import Notification
from src.notifications.domain.exceptions import NotificationSendingFailedError
from src.notifications.domain.vo import ChannelType, NotificationType
from src.notifications.resolvers import ChannelResolver
from src.notifications.services import NotificationService
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


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


@pytest.fixture
def notification_service(mock_session, mock_notification_repo, channel_resolver):
    return NotificationService(mock_session, mock_notification_repo, channel_resolver)


@pytest.fixture
def notification():
    return Notification(
        user_id=uuid4(),
        title="Test",
        message="Test message",
        type=NotificationType.TICKET_ASSIGNED,
    )


class TestNotificationServiceNotify:
    """
    Тесты для метода отправляющего уведомления в нужные каналы
    """

    @pytest.mark.asyncio
    async def test_notify_creates_and_sends_success(
            self,
            mock_session,
            notification,
            notification_service,
            mock_notification_repo,
            email_channel,
            in_app_channel,
    ):
        await notification_service.notify(notification)

        mock_session.commit.assert_awaited_once()

        created_notification = await mock_notification_repo.read(notification.id)

        assert created_notification is not None
        assert created_notification.title == notification.title

        email_channel.send.assert_awaited_once_with(notification)
        in_app_channel.send.assert_awaited_once_with(notification)

    @pytest.mark.asyncio
    async def test_notify_continues_sending_after_failure(
            self, notification, notification_service, email_channel, in_app_channel
    ):
        email_channel.send.side_effect = NotificationSendingFailedError("Fail 1")

        await notification_service.notify(notification)

        email_channel.send.assert_awaited_once_with(notification)
        in_app_channel.send.assert_awaited_once_with(notification)


class TestNotificationServiceMarkAsRead:
    """
    Тесты для пометить как прочитанное
    """

    @pytest.mark.asyncio
    async def test_mark_as_read_updates_unread_notification(
            self, notification, mock_session, notification_service, mock_notification_repo
    ):
        await mock_notification_repo.create(notification)

        await notification_service.mark_as_read(notification.id, read_by=notification.user_id)

        updated_notification = await mock_notification_repo.read(notification.id)

        assert updated_notification.read is True

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_does_nothing_if_already_read(
            self,
            notification,
            mock_session,
            notification_service,
            mock_notification_repo,
            caplog
    ):
        notification = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            type=NotificationType.TICKET_ASSIGNED,
            read=True,
        )
        await mock_notification_repo.create(notification)

        with caplog.at_level(logging.WARNING):
            await notification_service.mark_as_read(notification.id, read_by=notification.user_id)

        mock_session.commit.assert_not_awaited()
        assert f"Notification with ID {notification.id} already marked as read" in caplog.text

    @pytest.mark.asyncio
    async def test_mark_as_read_raises_not_found_error_when_notification_missing(
            self, notification_service, notification
    ):
        with pytest.raises(
                NotFoundError, match=f"Notification with ID {notification.id} not found"
        ):
            await notification_service.mark_as_read(notification.id, read_by=notification.user_id)
