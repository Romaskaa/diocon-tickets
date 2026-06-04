import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.domain.exceptions import NotFoundError
from .domain.entities import Notification
from .domain.exceptions import NotificationSendingFailedError
from .domain.repos import NotificationRepository
from .resolvers import ChannelResolver

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
            self,
            session: AsyncSession,
            repository: NotificationRepository,
            channel_resolver: ChannelResolver
    ) -> None:
        self.session = session
        self.repository = repository
        self.channel_resolver = channel_resolver

    async def notify(self, notification: Notification) -> None:
        """Отправка уведомления через все подходящие каналы"""

        # 1. Сохранение сущности
        await self.repository.create(notification)
        await self.session.commit()

        # 2. Отправка уведомления во все подходящие каналы
        channels = await self.channel_resolver.resolve(
            user_id=notification.user_id, notification_type=notification.type
        )
        for channel in channels:
            try:
                await channel.send(notification)
            except NotificationSendingFailedError:
                logger.exception("Notification sending failed")

    async def mark_as_read(self, notification_id: UUID, read_by: UUID) -> None:
        notification = await self.repository.read(notification_id)
        if notification is None:
            raise NotFoundError(f"Notification with ID {notification_id} not found")

        if not notification.read:
            notification.mark_as_read(read_by)
            await self.repository.upsert(notification)
            await self.session.commit()
        else:
            logger.warning("Notification with ID %s already marked as read", notification_id)
