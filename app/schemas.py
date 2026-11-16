import re
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
)

_LINK_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_URL_ADAPTER = TypeAdapter(AnyHttpUrl)
_TRAILING_PUNCTUATION = ".,;:!?"


def extract_cta_url(message: str) -> str:
    matches = _LINK_PATTERN.findall(message)
    if len(matches) != 1:
        raise ValueError("message must contain exactly one http(s) URL")

    url = matches[0].rstrip(_TRAILING_PUNCTUATION)
    for closing, opening in ((")", "("), ("]", "["), ("}", "{")):
        while url.endswith(closing) and url.count(closing) > url.count(opening):
            url = url[:-1]

    try:
        parsed_url = _URL_ADAPTER.validate_python(url)
    except ValidationError as exc:
        raise ValueError("message must contain a valid http(s) URL") from exc

    if not parsed_url.host:
        raise ValueError("message must contain a valid http(s) URL")
    return url


class PostingRequest(BaseModel):
    message: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Text to publish. Must contain exactly one valid HTTP or HTTPS URL."
            ),
            examples=["Check out our latest business platform: https://example.com"],
        ),
    ]

    @field_validator("message")
    @classmethod
    def validate_single_cta_url(cls, message: str) -> str:
        extract_cta_url(message)
        return message


class PlatformResult(BaseModel):
    platform: str = Field(description="Name of the publishing platform.")
    status: Literal["success", "failed"] = Field(
        description="Whether this platform accepted the post."
    )
    posted_url: str | None = Field(
        description="Public URL of the created post, or null when unavailable."
    )
    public_access: bool | None = Field(
        description=(
            "Whether the post is publicly accessible; null when the integration "
            "cannot determine visibility."
        )
    )
    date: str | None = Field(
        description="Provider acknowledgement date in YYYY-MM-DD format (IST)."
    )
    time: str | None = Field(
        description="Provider acknowledgement time in HH:MM:SS format (IST)."
    )
    error: str | None = Field(
        description="Non-secret failure reason, or null when status is success."
    )


class PostingResponse(BaseModel):
    success: bool = Field(
        description="True if at least one platform successfully accepted the post."
    )
    results: list[PlatformResult] = Field(
        description="One independent result for each configured platform integration."
    )
