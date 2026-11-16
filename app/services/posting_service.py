import asyncio
import logging

import httpx

from app.config import Settings
from app.platforms.base import IntegrationError, Publisher, failed_result
from app.platforms.bluesky import BlueskyPublisher
from app.platforms.linkedin import LinkedInPublisher
from app.platforms.mastodon import MastodonPublisher
from app.platforms.reddit import RedditPublisher
from app.platforms.x import XPublisher
from app.schemas import PlatformResult, PostingResponse

logger = logging.getLogger(__name__)


class PostingService:
    def __init__(self, settings: Settings) -> None:
        self.publishers: list[Publisher] = [
            MastodonPublisher(settings),
            BlueskyPublisher(settings),
            LinkedInPublisher(settings),
            XPublisher(settings),
            RedditPublisher(settings),
        ]

    async def post_all(
        self, message: str, client: httpx.AsyncClient
    ) -> PostingResponse:
        results = await asyncio.gather(
            *(
                self._publish_one(publisher, message, client)
                for publisher in self.publishers
            )
        )
        return PostingResponse(
            success=any(result.status == "success" for result in results),
            results=results,
        )

    async def _publish_one(
        self, publisher: Publisher, message: str, client: httpx.AsyncClient
    ) -> PlatformResult:
        try:
            return await publisher.publish(message, client)
        except IntegrationError as exc:
            logger.warning("Posting to %s failed: %s", publisher.name, exc)
            return failed_result(publisher.name, str(exc))
        except Exception as exc:
            logger.exception("Unexpected error while posting to %s", publisher.name)
            return failed_result(
                publisher.name, f"unexpected integration error ({type(exc).__name__})"
            )
