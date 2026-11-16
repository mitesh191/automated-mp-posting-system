from urllib.parse import urljoin

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


class RedditPublisher(Publisher):
    name = "Reddit"
    _API = "https://oauth.reddit.com/api/submit"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        token = self.settings.reddit_access_token
        subreddit = self.settings.reddit_subreddit
        if not token or not subreddit:
            raise IntegrationError("not configured")

        _, payload = await request_json(
            client,
            "POST",
            self._API,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.settings.reddit_user_agent,
            },
            data={
                "api_type": "json",
                "kind": "self",
                "resubmit": "true",
                "sr": subreddit,
                "text": message,
                "title": self.settings.reddit_post_title,
            },
        )
        reddit_response = required_object(payload, "json")
        errors = reddit_response.get("errors", [])
        if errors:
            raise IntegrationError("provider rejected the submission")
        post_data = required_object(reddit_response, "data")
        permalink = post_data.get("url")
        if not isinstance(permalink, str) or not permalink:
            raise IntegrationError("provider response is missing post URL")
        post_url = urljoin("https://www.reddit.com", permalink)
        if not post_url.startswith("https://www.reddit.com/"):
            raise IntegrationError("provider returned an invalid post URL")
        return successful_result(self.name, PublishedPost(url=post_url))
