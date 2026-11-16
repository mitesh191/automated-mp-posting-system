import re

import httpx

from app.config import Settings
from app.platforms.base import (
    IntegrationError,
    PublishedPost,
    Publisher,
    request_json,
    required_object,
    successful_result,
)
from app.schemas import PlatformResult

_NUMERIC_CHAT_ID_PATTERN = re.compile(r"-?\d+")
_PUBLIC_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{5,32}")


class TelegramPublisher(Publisher):
    name = "Telegram"
    _API = "https://api.telegram.org"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        token = self.settings.telegram_bot_token
        configured_chat_id = self.settings.telegram_chat_id
        if not token or not configured_chat_id:
            raise IntegrationError("not configured")

        chat_id = configured_chat_id.strip()
        is_public_username = chat_id.startswith("@") and bool(
            _PUBLIC_USERNAME_PATTERN.fullmatch(chat_id[1:])
        )
        if not is_public_username and not _NUMERIC_CHAT_ID_PATTERN.fullmatch(chat_id):
            raise IntegrationError("chat ID must be numeric or a public @username")

        _, payload = await request_json(
            client,
            "POST",
            f"{self._API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
        )
        if payload.get("ok") is not True:
            raise IntegrationError("provider rejected the message")

        result = required_object(payload, "result")
        chat = required_object(result, "chat")
        message_id = result.get("message_id")
        if (
            not isinstance(message_id, int)
            or isinstance(message_id, bool)
            or message_id <= 0
        ):
            raise IntegrationError("provider response is missing message_id")

        posted_url = None
        public_access = False
        username = chat.get("username")
        if (
            chat.get("type") in {"channel", "supergroup"}
            and isinstance(username, str)
            and _PUBLIC_USERNAME_PATTERN.fullmatch(username)
        ):
            posted_url = f"https://t.me/{username}/{message_id}"
            public_access = True

        return successful_result(
            self.name,
            PublishedPost(url=posted_url, public_access=public_access),
        )
