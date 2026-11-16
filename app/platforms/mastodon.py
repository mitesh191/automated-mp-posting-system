from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.config import Settings
from app.platforms.base import (
    IntegrationError,
    PublishedPost,
    Publisher,
    request_json,
    required_string,
    successful_result,
)
from app.schemas import PlatformResult


class MastodonPublisher(Publisher):
    name = "Mastodon"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        instance = self.settings.mastodon_instance_url
        token = self.settings.mastodon_access_token
        if not instance or not token:
            raise IntegrationError("not configured")
        parsed_instance = urlsplit(instance)
        if (
            parsed_instance.scheme != "https"
            or not parsed_instance.hostname
            or parsed_instance.username
            or parsed_instance.password
            or parsed_instance.query
            or parsed_instance.fragment
        ):
            raise IntegrationError("instance URL must be a valid HTTPS origin")

        _, payload = await request_json(
            client,
            "POST",
            f"{instance.rstrip('/')}/api/v1/statuses",
            data={"status": message, "visibility": "public"},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": str(uuid4()),
            },
        )
        post_url = required_string(payload, "url")
        return successful_result(self.name, PublishedPost(url=post_url))
