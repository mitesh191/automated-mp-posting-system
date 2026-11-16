import re
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.platforms.base import (
    IntegrationError,
    PublishedPost,
    Publisher,
    request_json,
    successful_result,
)
from app.schemas import PlatformResult

_WEBHOOK_PATH_PATTERN = re.compile(r"/api/webhooks/\d+/[A-Za-z0-9._-]+")


class DiscordPublisher(Publisher):
    name = "Discord"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        webhook_url = self.settings.discord_webhook_url
        if not webhook_url:
            raise IntegrationError("not configured")

        parsed_url = urlsplit(webhook_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "discord.com"
            or not _WEBHOOK_PATH_PATTERN.fullmatch(parsed_url.path)
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query not in {"", "wait=true"}
            or parsed_url.fragment
        ):
            raise IntegrationError("webhook URL must be a valid Discord webhook")

        await request_json(
            client,
            "POST",
            webhook_url,
            allow_empty=True,
            json={"content": message},
        )
        return successful_result(
            self.name,
            PublishedPost(url=None, public_access=False),
        )
