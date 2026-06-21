from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Any
from urllib import error, request
import xml.etree.ElementTree as ET


AI_ERA_RSS_URL = "https://link.baai.ac.cn/@AI_era.rss"


@dataclass(frozen=True, slots=True)
class RssItem:
    title: str
    url: str
    published_at: str
    summary: str
    categories: list[str]
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "summary": self.summary,
            "categories": self.categories,
            "source": self.source,
        }


def fetch_rss_items(url: str, *, limit: int = 25, timeout: int = 20) -> list[RssItem]:
    root = ET.fromstring(_fetch_text(url, timeout=timeout))
    channel = root.find("channel")
    if channel is None:
        return []

    source = _text(channel, "title") or url
    items: list[RssItem] = []
    for item in channel.findall("item"):
        item_url = _text(item, "link") or _text(item, "guid")
        summary = _clean_html(_text(item, "description"))
        title = _text(item, "title") or _derive_title(summary) or item_url
        if not item_url:
            continue
        items.append(
            RssItem(
                title=title,
                url=item_url,
                published_at=_normalize_date(_text(item, "pubDate")),
                summary=summary,
                categories=[category.text.strip() for category in item.findall("category") if category.text],
                source=source,
            )
        )
        if len(items) >= limit:
            break
    return items


def _fetch_text(url: str, *, timeout: int = 20) -> str:
    rss_request = request.Request(url, headers={"User-Agent": "DNA-DailyNewsAgent/2"})
    try:
        with request.urlopen(rss_request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"RSS request failed: {error_body}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"RSS request timed out after {timeout}s: {url}") from exc


def _text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _normalize_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, OverflowError):
        return value


def _clean_html(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"(https?://)\s+", r"\1", text)


def _derive_title(summary: str) -> str:
    if not summary:
        return ""
    first_sentence = re.split(r"[。.!?！？]", summary, maxsplit=1)[0].strip()
    return first_sentence[:80]
