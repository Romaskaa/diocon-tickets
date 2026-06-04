import logging

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.vk.com/method/"
API_VERSION = "5.199"


class VkApiClient:
    def __init__(self, service_token: str) -> None:
        self.service_token = service_token

    async def send_notification(
            self,
            user_ids: list[int],
            message: str,
            fragment: str | None = None,
            group_id: str | None = None,
    ):
        """Отправка уведомления пользователю мини-приложения"""

        if not user_ids:
            ...

        payload = {
            "user_ids": ",".join(map(str, user_ids)),
            "message": message[:254],
            "access_token": self.service_token,
            "v": API_VERSION,
        }
        if fragment is not None:
            payload["fragment"] = fragment
        if group_id is not None:
            payload["group_id"] = group_id

        async with aiohttp.ClientSession(base_url=BASE_URL) as session, session.post(
            url="notifications.sendMessage", data=payload
        ) as response:
            response.raise_for_status()
            data = await response.json()

        if "error" in data:
            error = data["error"]
