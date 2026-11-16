from datetime import UTC, datetime
from urllib.parse import quote

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
from app.schemas import PlatformResult, extract_cta_url


class BlueskyPublisher(Publisher):
    name = "Bluesky"
    _API = "https://bsky.social/xrpc"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        handle = self.settings.bluesky_handle
        app_password = self.settings.bluesky_app_password
        if not handle or not app_password:
            raise IntegrationError("not configured")

        _, session = await request_json(
            client,
            "POST",
            f"{self._API}/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_password},
        )
        access_token = required_string(session, "accessJwt")
        did = required_string(session, "did")

        url = extract_cta_url(message)
        url_start = message.index(url)
        byte_start = len(message[:url_start].encode("utf-8"))
        byte_end = byte_start + len(url.encode("utf-8"))
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "facets": [
                {
                    "$type": "app.bsky.richtext.facet",
                    "index": {"byteStart": byte_start, "byteEnd": byte_end},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
                }
            ],
        }
        _, post = await request_json(
            client,
            "POST",
            f"{self._API}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        uri = required_string(post, "uri")
        expected_uri_prefix = f"at://{did}/app.bsky.feed.post/"
        if not uri.startswith(expected_uri_prefix):
            raise IntegrationError("provider returned an unexpected post URI")
        rkey = uri.rsplit("/", maxsplit=1)[-1]
        if not rkey:
            raise IntegrationError("provider returned an invalid post URI")
        return successful_result(
            self.name,
            PublishedPost(
                url=f"https://bsky.app/profile/{quote(handle, safe='')}/post/{rkey}"
            ),
        )
