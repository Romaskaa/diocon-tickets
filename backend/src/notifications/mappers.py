from typing import Any

from fastapi.encoders import jsonable_encoder

from .domain.entities import Notification
from .schemas import NotificationResponse


def map_notification_to_dict(notification: Notification) -> dict[str, Any]:
    return jsonable_encoder({
        "id": notification.id,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "read": notification.read,
        "data": notification.data,
    })


def map_notification_to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        type=notification.type,
        read=notification.read,
        data=notification.data,
    )
