from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.platforms.base import (
    IntegrationError,
    PublishedPost,
    Publisher,
    successful_result,
)
from app.schemas import PlatformResult


class SlackPublisher(Publisher):
    name = "Slack"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        webhook_url = self.settings.slack_webhook_url
        if not webhook_url:
            raise IntegrationError("not configured")

        parsed_url = urlsplit(webhook_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "hooks.slack.com"
            or not parsed_url.path.startswith("/services/")
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise IntegrationError("webhook URL must be a valid Slack incoming webhook")

        try:
            response = await client.post(webhook_url, json={"text": message})
        except httpx.TimeoutException as exc:
            raise IntegrationError("request timed out") from exc
        except httpx.InvalidURL as exc:
            raise IntegrationError("invalid Slack webhook URL") from exc
        except httpx.RequestError as exc:
            raise IntegrationError("network request failed") from exc

        if not response.is_success:
            raise IntegrationError(f"provider returned HTTP {response.status_code}")
        if response.text.strip() != "ok":
            raise IntegrationError("provider rejected the message")

        return successful_result(
            self.name,
            PublishedPost(url=None, public_access=False),
        )
