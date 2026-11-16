import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mastodon_instance_url: str | None = None
    mastodon_access_token: str | None = None
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    linkedin_access_token: str | None = None
    linkedin_author_urn: str | None = None
    linkedin_version: str = "202610"
    x_user_access_token: str | None = None
    reddit_access_token: str | None = None
    reddit_subreddit: str | None = None
    reddit_post_title: str = "A quick update"
    reddit_user_agent: str = "automated-posting/1.0"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mastodon_instance_url=os.getenv("MASTODON_INSTANCE_URL"),
            mastodon_access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
            bluesky_handle=os.getenv("BLUESKY_HANDLE"),
            bluesky_app_password=os.getenv("BLUESKY_APP_PASSWORD"),
            linkedin_access_token=os.getenv("LINKEDIN_ACCESS_TOKEN"),
            linkedin_author_urn=os.getenv("LINKEDIN_AUTHOR_URN"),
            linkedin_version=os.getenv("LINKEDIN_VERSION", "202610"),
            x_user_access_token=os.getenv("X_USER_ACCESS_TOKEN"),
            reddit_access_token=os.getenv("REDDIT_ACCESS_TOKEN"),
            reddit_subreddit=os.getenv("REDDIT_SUBREDDIT"),
            reddit_post_title=os.getenv("REDDIT_POST_TITLE", "A quick update"),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "automated-posting/1.0"),
        )
