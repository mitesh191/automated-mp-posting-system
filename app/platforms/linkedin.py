from urllib.parse import quote

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


class LinkedInPublisher(Publisher):
    name = "LinkedIn"
    _API = "https://api.linkedin.com/rest/posts"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        token = self.settings.linkedin_access_token
        author = self.settings.linkedin_author_urn
        if not token or not author:
            raise IntegrationError("not configured")

        response, _ = await request_json(
            client,
            "POST",
            self._API,
            allow_empty=True,
            headers={
                "Authorization": f"Bearer {token}",
                "LinkedIn-Version": self.settings.linkedin_version,
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": author,
                "commentary": message,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
        post_id = response.headers.get("x-restli-id")
        if not post_id:
            raise IntegrationError("provider response is missing x-restli-id")
        post_url = f"https://www.linkedin.com/feed/update/{quote(post_id, safe=':')}/"
        return successful_result(self.name, PublishedPost(url=post_url))
