from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, parse, request


AGENTMAIL_API_BASE_URL = "https://api.agentmail.to/v0"


def fetch_messages(
    *,
    api_key: str | None = None,
    inbox_id: str | None = None,
    limit: int = 25,
    after: str | None = None,
) -> dict[str, Any]:
    resolved_api_key = api_key or os.getenv("AGENTMAIL_API_KEY")
    resolved_inbox_id = inbox_id or os.getenv("AGENTMAIL_INBOX_ID")
    if not resolved_api_key:
        raise RuntimeError("Environment variable 'AGENTMAIL_API_KEY' is required.")
    if not resolved_inbox_id:
        raise RuntimeError("Environment variable 'AGENTMAIL_INBOX_ID' is required.")

    query: dict[str, str] = {"limit": str(limit)}
    if after:
        query["after"] = after

    url = (
        f"{AGENTMAIL_API_BASE_URL}/inboxes/"
        f"{parse.quote(resolved_inbox_id, safe='')}/messages?"
        f"{parse.urlencode(query)}"
    )
    agentmail_request = request.Request(
        url,
        headers={"Authorization": f"Bearer {resolved_api_key}"},
        method="GET",
    )
    return _open_json(agentmail_request)


def message_summaries(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "message_id": message.get("message_id"),
            "timestamp": message.get("timestamp"),
            "from": message.get("from"),
            "subject": message.get("subject"),
            "preview": message.get("preview"),
        }
        for message in response.get("messages", [])
    ]


def _open_json(api_request: request.Request) -> dict[str, Any]:
    try:
        with request.urlopen(api_request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"AgentMail API request failed: {error_body}") from exc
    return json.loads(response_body)
