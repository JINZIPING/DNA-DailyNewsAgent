from __future__ import annotations

from app.tools.email_sender.resend import send_email as send_resend_email


def send_email(
    recipient: str,
    subject: str,
    body: str,
    api_key_env: str | None = None,
    sender_email: str | None = None,
) -> dict:
    return send_resend_email(
        recipient=recipient,
        subject=subject,
        body=body,
        api_key_env=api_key_env,
        sender_email=sender_email,
    )


__all__ = ["send_email"]
