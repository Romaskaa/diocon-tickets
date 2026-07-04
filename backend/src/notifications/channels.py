from typing import ClassVar, Protocol

import logging

from faststream.rabbit import RabbitBroker

from src.iam.domain.repos import UserRepository
from src.shared.domain.exceptions import EmailSendingFailedError
from src.shared.infra.mail import SmtpMailSender

from .domain.entities import Notification
from .domain.exceptions import NotificationSendingFailedError
from .domain.vo import ChannelType, NotificationType
from .mappers import map_notification_to_response

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    channel_type: ClassVar[ChannelType]

    async def send(self, notification: Notification) -> None:
        """Отправить уведомление через текущий канал"""


# Маппинг типов уведомлений к email шаблону
EMAIL_TEMPLATE_MAP: dict[NotificationType, str] = {
    NotificationType.TICKET_CREATED: "email/ticket_created.html",
    NotificationType.TICKET_ASSIGNED: "email/assigned.html",
    NotificationType.TICKET_STATUS_CHANGED: "email/ticket_status_changed.html",
}


class EmailChannel:
    channel_type = ChannelType.EMAIL

    def __init__(self, mail_sender: SmtpMailSender, user_repo: UserRepository) -> None:
        self.mail_sender = mail_sender
        self.user_repo = user_repo

    async def send(self, notification: Notification) -> None:
        user = await self.user_repo.read(notification.user_id)
        if user is None:
            return
        template_name = EMAIL_TEMPLATE_MAP.get(notification.type)
        if template_name is None:
            logger.warning(
                "No such template registered for this notification type - '%s'",
                notification.type.value
            )
        try:
            await self.mail_sender.send(
                to=user.email,
                subject=notification.title,
                plain_text=notification.message,
                template_name=template_name,
                context=None if template_name is None else notification.data,
            )
        except EmailSendingFailedError as e:
            raise NotificationSendingFailedError(
                "Error occurred while sending to email channel"
            ) from e


class InAppChannel:
    channel_type = ChannelType.IN_APP

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker

    async def send(self, notification: Notification) -> None:
        payload = map_notification_to_response(notification)
        await self.broker.publish(payload, queue="notifications.sse")
