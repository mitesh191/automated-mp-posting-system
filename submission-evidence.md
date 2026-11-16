# Submission API Example and Test Evidence

## Sample API request

The API reads platform credentials from the server's `.env` configuration.
Do not include provider tokens or webhook URLs in the request. This request
will attempt to post to every configured platform, so use a test message and
destination.

Run the API first with `docker compose up --build -d`, then execute in
PowerShell:

```powershell
$body = @{
  message = "Submission test from my posting API: https://example.com"
} | ConvertTo-Json -Compress

$response = Invoke-RestMethod `
  -Uri "http://localhost:4000/posting" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 6
```

## Sample API response

This response is illustrative only. Real platform statuses, URLs, dates, and
errors depend on the configured credentials and provider responses.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@demo_user/12345",
      "public_access": null,
      "date": "2026-11-16",
      "time": "19:45:00",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/demo.bsky.social/post/abc123",
      "public_access": null,
      "date": "2026-11-16",
      "time": "19:45:01",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": null,
      "public_access": false,
      "date": "2026-11-16",
      "time": "19:45:02",
      "error": null
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": null,
      "public_access": false,
      "date": "2026-11-16",
      "time": "19:45:03",
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

## Automated test log

The following checks were run locally. Provider HTTP requests in the automated
tests are mocked; this log demonstrates test and code-quality checks, not live
posts to the platforms.

```text
> python -m pytest -q
10 passed, 82 warnings in 2.16s

> python -m ruff check app tests
All checks passed!

> python -m ruff format --check app tests
14 files already formatted
```

Pytest reported deprecation warnings from `pytest-asyncio` under Python 3.14;
the test run completed successfully.

## Optional live-run screenshot

To capture a live request/response for submission, open
`http://localhost:4000/docs`, expand `POST /posting`, choose **Try it out**,
enter a test message with exactly one valid URL, and click **Execute**. This
publishes to the configured destinations. Capture the response panel or the
PowerShell output from the command above. Container logs show startup,
access, and error information; they do not include the full JSON response by
default. View them with:

```powershell
docker compose logs --tail=100 api
```
