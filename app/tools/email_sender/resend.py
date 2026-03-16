from __future__ import annotations

import os
import re
from typing import Any, cast
from urllib.parse import urlparse

import markdown
import resend


def send_email(
    recipient: str,
    subject: str,
    body: str,
    api_key_env: str | None = None,
    sender_email: str | None = None,
) -> dict:
    if not api_key_env:
        raise RuntimeError("Resend requires an api_key_env config value.")
    if not sender_email:
        raise RuntimeError("Resend requires a sender_email config value.")

    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Environment variable '{api_key_env}' is not set.")

    resend_client = cast(Any, resend)
    resend_client.api_key = api_key
    response = resend_client.Emails.send(
        {
            "from": sender_email,
            "to": [recipient],
            "subject": subject,
            "html": _render_email_html(subject, body),
        }
    )
    return {
        "recipient": recipient,
        "subject": subject,
        "provider": "resend",
        "response": response,
        "status": "sent",
    }


def _render_email_html(subject: str, body: str) -> str:
    cleaned_body = _strip_bare_urls(body)
    content_html = markdown.markdown(
        cleaned_body,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    return f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f4f5;color:#111827;">
    <div style="max-width:720px;margin:0 auto;padding:32px 20px;">
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:32px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.65;">
        <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin-bottom:16px;">
          DNA Daily News Agent
        </div>
        <div style="font-size:16px;">
          {content_html}
        </div>
      </div>
    </div>
  </body>
</html>
"""


def _strip_bare_urls(markdown_text: str) -> str:
    placeholders: list[str] = []

    def preserve_markdown_link(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"__LINK_PLACEHOLDER_{len(placeholders) - 1}__"

    preserved = re.sub(r"\[[^\]]+\]\([^)]+\)", preserve_markdown_link, markdown_text)

    def replace_bare_url(match: re.Match[str]) -> str:
        url = match.group(0)
        parsed = urlparse(url)
        label = parsed.netloc or "link"
        return f"{label}"

    cleaned = re.sub(r"https?://[^\s)>\]]+", replace_bare_url, preserved)

    for index, original in enumerate(placeholders):
        cleaned = cleaned.replace(f"__LINK_PLACEHOLDER_{index}__", original)
    return cleaned
