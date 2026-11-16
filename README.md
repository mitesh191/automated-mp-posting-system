# Automated Multi-Platform Posting API

A Dockerized FastAPI service that accepts one short message and attempts to
publish it to Mastodon, Bluesky, Telegram, Slack, and Discord.
Each platform is handled independently: a failure at one provider does not
prevent attempts to the others.

This project integrates platforms that provide APIs for publishing content.
General-purpose LLM APIs are not publishing destinations and are not included.

## Requirements

- Docker Desktop on Windows or macOS, or Docker Engine with the Docker Compose
  plugin on Linux.
- A provider account and API credentials for each platform you want to use.
- Internet access from Docker to download the Python base image and application
  dependencies during the first build.

The Docker image uses Python 3.12 and installs the runtime packages listed in
[`requirements.txt`](requirements.txt). You do not need to install Python on
your computer to run the service with Docker.

## Install Docker

### Windows

1. Enable hardware virtualization in your computer's firmware if it is not
   already enabled.
2. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
   Use the WSL 2 backend when prompted; the installer will guide you if WSL
   needs to be enabled or updated.
3. Start Docker Desktop and wait until it reports that the engine is running.
4. Open PowerShell and verify Docker and Compose are available:

   ```powershell
   docker --version
   docker compose version
   docker info
   ```

### macOS

Install and start [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), then verify it with `docker --version` and `docker compose version`.

### Linux

Install Docker Engine and the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/), then verify them with `docker --version` and `docker compose version`.

## Get the project

After publishing the project to GitHub, clone it and change into its folder.
Replace `OWNER/REPOSITORY` with the GitHub account and repository name:

```sh
git clone https://github.com/mitesh191/automated-mp-posting-system.git
cd REPOSITORY
```

Run the remaining commands from this project directory.

## Configure API credentials

Docker Compose reads an optional `.env` file from the project root. Create it
from the example:

**PowerShell**

```powershell
Copy-Item .env.example .env
notepad .env
```

**macOS/Linux**

```sh
cp .env.example .env
```

Edit `.env` and add credentials only for the platforms you want to use. Each
provider is optional, but a platform without its required settings will return
a `failed` result with `not configured`.

| Platform | Required variables |
|---|---|
| Mastodon | `MASTODON_INSTANCE_URL`, `MASTODON_ACCESS_TOKEN` |
| Bluesky | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Slack | `SLACK_WEBHOOK_URL` |
| Discord | `DISCORD_WEBHOOK_URL` |

Use a Mastodon token with status-writing permission and a Bluesky app password
(not your account password). Provider access, reviews, and rate limits are
controlled by the individual platforms.

For Telegram, create a bot with [BotFather](https://t.me/BotFather) and set
`TELEGRAM_CHAT_ID` to a numeric chat ID or a public channel username (including
`@`). The bot must be able to send messages to that chat. Public channels and
public supergroups return a `t.me` link; private chats return no public URL and
have `public_access: false`. Accordingly, `posted_url` is `null` whenever
Telegram does not return a public username for the destination.

For Slack, create an incoming webhook for the destination channel and set
`SLACK_WEBHOOK_URL` to its URL. Incoming webhooks are bound to a Slack
workspace channel and return only an acknowledgement, not a message permalink.
Slack results therefore use `posted_url: null` and
`public_access: false`.

For Discord, set `DISCORD_WEBHOOK_URL` to an incoming webhook for the
destination channel. Although Discord can return message details when the
webhook URL includes `?wait=true`, the integration currently does not use
those details to build a permalink. Discord results therefore use
`posted_url: null` and `public_access: false`.

## Build and run with Docker

Run these commands from the project root (the directory containing
`compose.yaml`):

```sh
docker compose up --build -d
docker compose ps
```

The Compose configuration binds the service to your local machine at
`127.0.0.1:4000`. Confirm the health endpoint:

**PowerShell**

```powershell
Invoke-RestMethod http://localhost:4000/health
```

**macOS/Linux**

```sh
curl http://localhost:4000/health
```

Expected response:

```json
{"status":"ok"}
```

Open the interactive API documentation at
[http://localhost:4000/docs](http://localhost:4000/docs).

Useful container commands:

```sh
docker compose logs -f api
docker compose down
```

`docker compose down` stops and removes the project container and network. It
does not delete your source files or `.env`.

## API reference

Base URL: `http://localhost:4000`

### `POST /posting`

Attempts to publish a message to Mastodon, Bluesky, Telegram, Slack, and
Discord. Platform selection is configured by the service and cannot be supplied
in the request.

**Request headers**

| Header | Required | Value |
|---|---|---|
| `Content-Type` | Yes | `application/json` |
| `Accept` | No | `application/json` |

**Request body**

| Field | Type | Constraints |
|---|---|---|
| `message` | string | Required; 1-200 characters; exactly one valid URL using `http://` or `https://` |

Example:

```json
{
  "message": "Check out our latest business platform: https://example.com"
}
```

Example in PowerShell:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:4000/posting `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"Check out our latest business platform: https://example.com"}'
```

**Successful request response (`200 OK`)**

HTTP `200` means the request was valid and the service completed its attempts;
it does not mean every platform succeeded. Each platform is handled
independently, and `success` is `true` when at least one platform succeeds.
It is `false` if all platform attempts fail or are unconfigured. Platform
failures are reported in `results` and do not change the HTTP status.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@example/123456",
      "public_access": null,
      "date": "2026-11-16",
      "time": "19:20:00",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/example.bsky.social/post/abc123",
      "public_access": null,
      "date": "2026-11-16",
      "time": "19:20:01",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/example_channel/44",
      "public_access": true,
      "date": "2026-11-16",
      "time": "19:20:02",
      "error": null
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": null,
      "public_access": false,
      "date": "2026-11-16",
      "time": "19:20:03",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "provider returned HTTP 403"
    }
  ]
}
```

The example is illustrative; actual platform results depend on configuration
and provider responses. Results are returned in this order: Mastodon, Bluesky,
Telegram, Slack, Discord.

**Response fields**

| Field | Type | Meaning |
|---|---|---|
| `success` | boolean | `true` if at least one platform succeeded; otherwise `false`. |
| `results` | array | One result for each of the five integrations. |
| `results[].platform` | string | Platform name. |
| `results[].status` | string | `success` or `failed`. |
| `results[].posted_url` | string or `null` | Public URL of the published post, if the integration provides one. |
| `results[].public_access` | boolean or `null` | Public accessibility when known; `null` means it could not be determined. |
| `results[].date` | string or `null` | Successful provider acknowledgment date in `YYYY-MM-DD` format, IST (UTC+05:30). |
| `results[].time` | string or `null` | Successful provider acknowledgment time in `HH:MM:SS` format, IST (UTC+05:30). |
| `results[].error` | string or `null` | Failure reason; `null` on success. |

`posted_url` may be `null` even when `status` is `success`: Slack webhooks do
not return a message permalink, Discord message details are not currently used
to construct one, and Telegram provides a public link only when the destination
has a public username. Mastodon and Bluesky links are returned by their APIs;
their `public_access` value is `null` because the service does not independently
verify visibility.

**HTTP error responses**

| Status | Meaning |
|---|---|
| `422 Unprocessable Entity` | The JSON body is missing or invalid; for example, `message` is empty, exceeds 200 characters, or has zero/multiple/invalid URLs. No platform attempts are made. FastAPI returns a `detail` array identifying the invalid request field. |
| `500 Internal Server Error` | An unexpected server error prevented the request from being handled. Individual provider errors normally appear in a `200` response instead. |

Example `422` response for a message without a URL:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, message must contain exactly one http(s) URL",
      "input": "A message without a link",
      "ctx": {"error": {}}
    }
  ]
}
```

Provider error strings are returned per result, for example `"not configured"`,
`"request timed out"`, `"network request failed"`, or
`"provider returned HTTP 403"`. Provider-specific messages can vary. Failed
results have `posted_url`, `date`, and `time` set to `null`.

### `GET /health`

Checks whether the API process is responding. This does not verify provider
credentials or external platform availability.

**Response (`200 OK`)**

```json
{"status":"ok"}
```

Interactive OpenAPI documentation is available at
[http://localhost:4000/docs](http://localhost:4000/docs); the machine-readable
OpenAPI schema is at [http://localhost:4000/openapi.json](http://localhost:4000/openapi.json).

**Operational notes**

- Each accepted request attempts to post to all five integrations, including
  unconfigured ones, which return a `failed` result with `"not configured"`.
- Provider-specific rate limits and availability are controlled by each
  provider. The API does not retry failed posts.
- The endpoint is not idempotent. Retrying a request can publish duplicate
  messages.

## Optional: run without Docker

For local development, install Python 3.12, then create a virtual environment
and install the runtime requirements:

**PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 4000 --env-file .env
```

The `.env` file must exist for this command. Uvicorn reads it using the
`--env-file` option.

## Development checks

Install the development requirements (which include the runtime requirements,
pytest, pytest-asyncio, and Ruff):

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check app tests
python -m ruff format --check app tests
```

Provider calls in the tests are mocked; running the tests does not publish real
content.

## Official API references

- [Mastodon: Create a status](https://docs.joinmastodon.org/methods/statuses/#create)
- [Bluesky: Create a record](https://docs.bsky.app/docs/api/com-atproto-repo-create-record)
- [Telegram: sendMessage](https://core.telegram.org/bots/api#sendmessage)
- [Slack: Incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)
- [Discord: Execute Webhook](https://discord.com/developers/docs/resources/webhook#execute-webhook)
