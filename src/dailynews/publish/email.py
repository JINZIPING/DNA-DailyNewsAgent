from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib import error, request


DEFAULT_FROM_NAME = "DNA Daily Brief"
DEFAULT_FROM_EMAIL = "dna@sharkshark-studio.xyz"
RESEND_EMAILS_URL = "https://api.resend.com/emails"


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    from_name: str = DEFAULT_FROM_NAME
    from_email: str = DEFAULT_FROM_EMAIL


def send_email(
    message: EmailMessage,
    *,
    api_key: str | None = None,
    api_key_env: str = "RESEND_API_KEY",
) -> dict[str, object]:
    resolved_api_key = api_key or os.getenv(api_key_env)
    if not resolved_api_key:
        raise RuntimeError(f"Environment variable '{api_key_env}' is required.")

    payload = {
        "from": f"{message.from_name} <{message.from_email}>",
        "to": [message.to],
        "subject": message.subject,
        "html": message.html,
    }
    body = json.dumps(payload).encode("utf-8")
    resend_request = request.Request(
        RESEND_EMAILS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {resolved_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "DNA-DailyNewsAgent/2",
        },
        method="POST",
    )

    try:
        with request.urlopen(resend_request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Resend email request failed: {error_body}") from exc

    return json.loads(response_body)
