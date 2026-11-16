from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Protocol

import httpx

from app.schemas import PlatformResult

INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


class IntegrationError(Exception):
    pass


class Publisher(Protocol):
    name: str

    async def publish(
        self, message: str, client: httpx.AsyncClient
    ) -> PlatformResult: ...


@dataclass(frozen=True)
class PublishedPost:
    url: str | None
    public_access: bool | None = None


def successful_result(platform: str, post: PublishedPost) -> PlatformResult:
    published_at = datetime.now(UTC).astimezone(INDIA_TIMEZONE)
    return PlatformResult(
        platform=platform,
        status="success",
        posted_url=post.url,
        public_access=post.public_access,
        date=published_at.date().isoformat(),
        time=published_at.strftime("%H:%M:%S"),
        error=None,
    )


def failed_result(platform: str, error: str) -> PlatformResult:
    return PlatformResult(
        platform=platform,
        status="failed",
        posted_url=None,
        public_access=False,
        date=None,
        time=None,
        error=error,
    )


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    allow_empty: bool = False,
    **kwargs: Any,
) -> tuple[httpx.Response, dict[str, Any]]:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise IntegrationError("request timed out") from exc
    except httpx.InvalidURL as exc:
        raise IntegrationError("invalid integration URL configuration") from exc
    except httpx.RequestError as exc:
        raise IntegrationError("network request failed") from exc

    if not response.is_success:
        raise IntegrationError(f"provider returned HTTP {response.status_code}")

    if allow_empty and not response.content:
        return response, {}

    try:
        payload = response.json()
    except ValueError as exc:
        raise IntegrationError("provider returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise IntegrationError("provider returned an unexpected response")
    return response, payload


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise IntegrationError(f"provider response is missing {key}")
    return value


def required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise IntegrationError(f"provider response is missing {key}")
    return value
