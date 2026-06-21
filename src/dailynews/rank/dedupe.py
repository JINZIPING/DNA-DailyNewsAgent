from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dailynews.core.models import NormalizedItem


TRACKING_PARAMS = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref"}


def dedupe_items(items: list[NormalizedItem]) -> list[NormalizedItem]:
    best_by_key: dict[str, NormalizedItem] = {}
    for item in items:
        key = dedupe_key(item)
        current = best_by_key.get(key)
        if current is None or _quality_score(item) > _quality_score(current):
            best_by_key[key] = item
    return list(best_by_key.values())


def dedupe_key(item: NormalizedItem) -> str:
    normalized_url = normalize_url(item.url)
    if normalized_url:
        return f"url:{normalized_url}"
    return f"title:{normalize_title(item.title)}"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    lowered = title.lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", lowered)).strip()


def _quality_score(item: NormalizedItem) -> tuple[int, int, int]:
    official = 1 if item.source_type in {"rss", "rsshub"} else 0
    content_len = len(item.content or item.summary)
    has_url = 1 if item.url else 0
    return official, content_len, has_url

