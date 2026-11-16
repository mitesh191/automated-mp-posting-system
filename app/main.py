from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request

from app.config import Settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService


def create_app(
    settings: Settings | None = None,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0), transport=http_transport
        ) as client:
            app.state.http_client = client
            yield

    app = FastAPI(
        title="Automated Multi-Platform Posting API",
        version="1.0.0",
        description=(
            "Publishes one validated message to the configured Mastodon, Bluesky, "
            "Telegram, Slack, and Discord integrations. Provider failures are "
            "reported per platform; they do not fail the HTTP request."
        ),
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    @app.post(
        "/posting",
        response_model=PostingResponse,
        summary="Publish a message to configured platforms",
        description=(
            "Accepts a message of 1-200 characters containing exactly one valid "
            "HTTP(S) URL. The service attempts all five providers independently. "
            "Provider-level failures are included in the 200 response; HTTP 422 "
            "indicates invalid request data."
        ),
        responses={
            500: {"description": "Unexpected server error prevented request handling."}
        },
    )
    async def create_post(payload: PostingRequest, request: Request) -> PostingResponse:
        service = PostingService(request.app.state.settings)
        return await service.post_all(payload.message, request.app.state.http_client)

    @app.get(
        "/health",
        summary="Check API health",
        description="Returns whether the API process is responding; does not test providers.",
    )
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
