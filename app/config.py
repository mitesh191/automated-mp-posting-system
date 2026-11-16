import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mastodon_instance_url: str | None = None
    mastodon_access_token: str | None = None
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mastodon_instance_url=os.getenv("MASTODON_INSTANCE_URL"),
            mastodon_access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
            bluesky_handle=os.getenv("BLUESKY_HANDLE"),
            bluesky_app_password=os.getenv("BLUESKY_APP_PASSWORD"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        )
