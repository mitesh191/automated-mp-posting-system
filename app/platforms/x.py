import httpx

from app.config import Settings
from app.platforms.base import (
    IntegrationError,
    PublishedPost,
    Publisher,
    request_json,
    required_object,
    required_string,
    successful_result,
)
from app.schemas import PlatformResult


class XPublisher(Publisher):
    name = "X"
    _API = "https://api.x.com/2/tweets"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        token = self.settings.x_user_access_token
        if not token:
            raise IntegrationError("not configured")

        _, payload = await request_json(
            client,
            "POST",
            self._API,
            headers={"Authorization": f"Bearer {token}"},
            json={"text": message},
        )
        post_id = required_string(required_object(payload, "data"), "id")
        return successful_result(
            self.name,
            PublishedPost(url=f"https://x.com/i/status/{post_id}"),
        )
