"""Publishing adapters."""

from dailynews.publish.email import (
    DEFAULT_FROM_EMAIL,
    DEFAULT_FROM_NAME,
    EmailMessage,
    send_email,
)

__all__ = [
    "DEFAULT_FROM_EMAIL",
    "DEFAULT_FROM_NAME",
    "EmailMessage",
    "send_email",
]

