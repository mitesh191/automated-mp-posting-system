import json
from datetime import UTC
from datetime import datetime as DateTime

import httpx
import pytest

import app.platforms.base as platform_base
from app.config import Settings
from app.main import create_app


def configured_settings() -> Settings:
    return Settings(
        mastodon_instance_url="https://mastodon.example",
        mastodon_access_token="mastodon-token",
        bluesky_handle="poster.example",
        bluesky_app_password="bluesky-password",
        telegram_bot_token="telegram-token",
        telegram_chat_id="@testchannel",
        slack_webhook_url=(
            "https://hooks.slack.com/services/T00000000/B00000000/test-secret"
        ),
        discord_webhook_url=(
            "https://discord.com/api/webhooks/123456789012345678/fakeWebhookToken"
            "?wait=true"
        ),
    )


def test_successful_post_timestamps_use_india_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_utc = DateTime(2026, 11, 16, 20, 30, tzinfo=UTC)

    class FrozenDateTime:
        @staticmethod
        def now(tz: object) -> DateTime:
            return fixed_utc

    monkeypatch.setattr(platform_base, "datetime", FrozenDateTime)
    result = platform_base.successful_result(
        "Test", platform_base.PublishedPost(url=None)
    )

    assert result.date == "2026-11-17"
    assert result.time == "02:00:00"


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
        if request.url.host == "api.telegram.org":
            return httpx.Response(403, json={"ok": False})
        if request.url.host == "hooks.slack.com":
            assert request.url.path == "/services/T00000000/B00000000/test-secret"
            assert json.loads(request.content) == {
                "text": "Try this https://example.com today"
            }
            return httpx.Response(200, text="ok")
        if request.url.host == "discord.com":
            assert request.url.path == (
                "/api/webhooks/123456789012345678/fakeWebhookToken"
            )
            assert request.url.query == b"wait=true"
            assert json.loads(request.content) == {
                "content": "Try this https://example.com today"
            }
            return httpx.Response(
                200, json={"id": "123456789012345679", "channel_id": "1234"}
            )
        raise AssertionError(f"unexpected request host: {request.url.host}")

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
        "failed",
        "success",
        "success",
    ]
    assert body["results"][2]["error"] == "provider returned HTTP 403"
    assert "mastodon.example" in requested_hosts
    assert "bsky.social" in requested_hosts
    assert "api.telegram.org" in requested_hosts
    assert "hooks.slack.com" in requested_hosts
    assert "discord.com" in requested_hosts
    assert body["results"][1]["posted_url"].endswith("/post/post1")
    assert body["results"][3]["posted_url"] is None
    assert body["results"][4]["posted_url"] is None
    assert [result["public_access"] for result in body["results"]] == [
        None,
        None,
        False,
        False,
        False,
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
async def test_telegram_rejects_invalid_chat_id_without_request() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(500)

    app = create_app(
        settings=Settings(
            telegram_bot_token="telegram-token",
            telegram_chat_id="private-chat-id",
        ),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Test https://example.com"}
        )

    telegram_result = response.json()["results"][2]
    assert telegram_result["status"] == "failed"
    assert telegram_result["error"] == "chat ID must be numeric or a public @username"
    assert requested_hosts == []


@pytest.mark.asyncio
async def test_telegram_numeric_chat_id_can_succeed_without_public_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.telegram.org"
        assert json.loads(request.content) == {
            "chat_id": "7942595830",
            "text": "Test https://example.com",
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 46,
                    "chat": {"id": 7942595830, "type": "private"},
                },
            },
        )

    app = create_app(
        settings=Settings(
            telegram_bot_token="telegram-token",
            telegram_chat_id="7942595830",
        ),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Test https://example.com"}
        )

    result = response.json()["results"][2]
    assert result["status"] == "success"
    assert result["posted_url"] is None
    assert result["public_access"] is False


@pytest.mark.asyncio
async def test_slack_rejects_non_slack_webhook_without_request() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(500)

    app = create_app(
        settings=Settings(slack_webhook_url="https://example.com/webhook"),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Test https://example.com"}
        )

    slack_result = response.json()["results"][3]
    assert slack_result["status"] == "failed"
    assert slack_result["error"] == "webhook URL must be a valid Slack incoming webhook"
    assert requested_hosts == []


@pytest.mark.asyncio
async def test_discord_rejects_non_discord_webhook_without_request() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(500)

    app = create_app(
        settings=Settings(discord_webhook_url="https://example.com/webhook"),
        http_transport=httpx.MockTransport(handler),
    )
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/posting", json={"message": "Test https://example.com"}
        )

    discord_result = response.json()["results"][4]
    assert discord_result["status"] == "failed"
    assert discord_result["error"] == "webhook URL must be a valid Discord webhook"
    assert requested_hosts == []


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
        if request.url.host == "api.telegram.org":
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 45,
                        "chat": {
                            "type": "channel",
                            "username": "testchannel",
                        },
                    },
                },
            )
        if request.url.host == "hooks.slack.com":
            return httpx.Response(200, text="ok")
        if request.url.host == "discord.com":
            return httpx.Response(204)
        raise AssertionError(f"unexpected request host: {request.url.host}")

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
    assert "mastodon.example" in requested_hosts
    assert "bsky.social" in requested_hosts
    assert "api.telegram.org" in requested_hosts
    assert "hooks.slack.com" in requested_hosts
    assert "discord.com" in requested_hosts


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
