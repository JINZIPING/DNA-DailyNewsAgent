from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from dailynews.core.models import NormalizedItem


def normalize_records(records: Any, *, source_id: str = "unknown", source_type: str = "unknown") -> list[NormalizedItem]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    raw_items = _extract_items(records)
    normalized: list[NormalizedItem] = []
    for raw in raw_items:
        item = _normalize_one(raw, source_id=source_id, source_type=source_type, fetched_at=fetched_at)
        if item:
            normalized.append(item)
    return normalized


def _extract_items(records: Any) -> list[dict[str, Any]]:
    if isinstance(records, list):
        return [dict(item) for item in records if isinstance(item, dict)]
    if isinstance(records, dict):
        for key in ("items", "messages", "entries", "data"):
            value = records.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _normalize_one(
    raw: dict[str, Any],
    *,
    source_id: str,
    source_type: str,
    fetched_at: str,
) -> NormalizedItem | None:
    title = _first_text(raw, "title", "subject")
    url = _first_text(raw, "url", "link")
    summary = _first_text(raw, "summary", "description", "preview")
    content = _first_text(raw, "content", "text", "body", "extracted_text") or summary
    published_at = _first_text(raw, "published_at", "published", "pubDate", "timestamp", "created_at")
    source_name = _first_text(raw, "source", "source_name", "from") or source_id
    categories = _list_text(raw.get("categories") or raw.get("category") or [])

    if not title and summary:
        title = summary[:120]
    if not title:
        return None

    stable_key = url or _first_text(raw, "message_id", "id") or f"{source_id}:{title}"
    return NormalizedItem(
        id=_stable_id(source_id, stable_key),
        source_id=source_id,
        source_type=source_type,
        source_name=source_name,
        title=title,
        url=url,
        published_at=published_at,
        summary=summary,
        content=content,
        categories=categories,
        fetched_at=fetched_at,
        raw=raw,
    )


def _first_text(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _list_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _stable_id(source_id: str, key: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{key}".encode("utf-8")).hexdigest()
    return digest[:16]

