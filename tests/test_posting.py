import httpx
import pytest

from app.config import Settings
from app.main import create_app


def configured_settings() -> Settings:
    return Settings(
        mastodon_instance_url="https://mastodon.example",
        mastodon_access_token="mastodon-token",
        bluesky_handle="poster.example",
        bluesky_app_password="bluesky-password",
        linkedin_access_token="linkedin-token",
        linkedin_author_urn="urn:li:person:123",
        x_user_access_token="x-token",
        reddit_access_token="reddit-token",
        reddit_subreddit="test",
    )


@pytest.mark.asyncio
async def test_validation_rejects_missing_or_multiple_links() -> None:
    app = create_app(settings=Settings())
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        no_link = await client.post("/posting", json={"message": "Hello world"})
        two_links = await client.post(
            "/posting",
            json={"message": "One https://one.example and https://two.example"},
        )
        invalid_url = await client.post("/posting", json={"message": "Broken https://"})
        too_long = await client.post(
            "/posting",
            json={"message": f"{'x' * 181} https://example.com"},
        )
        at_limit = await client.post(
            "/posting",
            json={"message": f"{'x' * 180} https://example.com"},
        )

    assert no_link.status_code == 422
    assert two_links.status_code == 422
    assert invalid_url.status_code == 422
    assert too_long.status_code == 422
    assert at_limit.status_code == 200


@pytest.mark.asyncio
async def test_each_platform_is_attempted_when_some_fail() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "mastodon.example":
            return httpx.Response(200, json={"url": "https://mastodon.example/@a/1"})
        if request.url.host == "bsky.social":
            if request.url.path.endswith("createSession"):
                return httpx.Response(
                    200, json={"accessJwt": "session-token", "did": "did:plc:a"}
                )
            return httpx.Response(
                200, json={"uri": "at://did:plc:a/app.bsky.feed.post/post1"}
            )
        if request.url.host == "api.linkedin.com":
            return httpx.Response(
                201, headers={"x-restli-id": "urn:li:share:123"}, json={}
            )
        if request.url.host == "api.x.com":
            return httpx.Response(403, json={"detail": "forbidden"})
        return httpx.Response(
            200,
            json={
                "json": {
                    "errors": [],
                    "data": {"url": "/r/test/comments/abc/quick_update/"},
                }
            },
        )

    app = create_app(
        settings=configured_settings(),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting",
            json={"message": "Try this https://example.com today"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert [result["status"] for result in body["results"]] == [
        "success",
        "success",
        "success",
        "failed",
        "success",
    ]
    assert body["results"][3]["error"] == "provider returned HTTP 403"
    assert "api.linkedin.com" in requested_hosts
    assert "oauth.reddit.com" in requested_hosts
    assert body["results"][1]["posted_url"].endswith("/post/post1")
    assert body["results"][4]["posted_url"].startswith("https://www.reddit.com/")
    assert [result["public_access"] for result in body["results"]] == [
        None,
        None,
        None,
        False,
        None,
    ]


@pytest.mark.asyncio
async def test_unconfigured_platforms_return_failures_without_api_calls() -> None:
    app = create_app(settings=Settings())
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "A message https://example.com"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert len(body["results"]) == 5
    assert all(result["status"] == "failed" for result in body["results"])
    assert all(result["error"] == "not configured" for result in body["results"])
    assert all(result["public_access"] is False for result in body["results"])


@pytest.mark.asyncio
async def test_unexpected_provider_error_does_not_stop_other_platforms() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "mastodon.example":
            raise RuntimeError("unexpected test transport error")
        if request.url.host == "bsky.social":
            if request.url.path.endswith("createSession"):
                return httpx.Response(
                    200, json={"accessJwt": "session-token", "did": "did:plc:a"}
                )
            return httpx.Response(
                200, json={"uri": "at://did:plc:a/app.bsky.feed.post/post1"}
            )
        if request.url.host == "api.linkedin.com":
            return httpx.Response(
                201, headers={"x-restli-id": "urn:li:share:123"}, content=b""
            )
        if request.url.host == "api.x.com":
            return httpx.Response(200, json={"data": {"id": "123"}})
        return httpx.Response(
            200,
            json={
                "json": {
                    "errors": [],
                    "data": {"url": "/r/test/comments/abc/quick_update/"},
                }
            },
        )

    app = create_app(
        settings=configured_settings(),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting",
            json={"message": "Try this https://example.com today"},
        )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["status"] for result in results] == [
        "failed",
        "success",
        "success",
        "success",
        "success",
    ]
    assert results[0]["error"] == "unexpected integration error (RuntimeError)"
    assert "api.linkedin.com" in requested_hosts
    assert "oauth.reddit.com" in requested_hosts


@pytest.mark.asyncio
async def test_mastodon_rejects_non_https_instance_before_sending_token() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(500)

    app = create_app(
        settings=Settings(
            mastodon_instance_url="http://mastodon.example",
            mastodon_access_token="must-not-be-sent",
        ),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Try https://example.com"}
        )

    mastodon_result = response.json()["results"][0]
    assert mastodon_result["status"] == "failed"
    assert mastodon_result["error"] == "instance URL must be a valid HTTPS origin"
    assert requested_hosts == []


@pytest.mark.asyncio
async def test_empty_linkedin_error_response_preserves_http_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.linkedin.com"
        return httpx.Response(403, content=b"")

    app = create_app(
        settings=Settings(
            linkedin_access_token="linkedin-token",
            linkedin_author_urn="urn:li:person:123",
        ),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Try https://example.com"}
        )

    linkedin_result = response.json()["results"][2]
    assert linkedin_result["status"] == "failed"
    assert linkedin_result["error"] == "provider returned HTTP 403"
