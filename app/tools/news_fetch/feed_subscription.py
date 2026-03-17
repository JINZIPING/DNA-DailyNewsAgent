from __future__ import annotations

from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import urlparse

import feedparser


class FeedSubscriptionMethod:
    ARTICLE_FIELDS = ("title", "url", "source", "text", "keyword_matches", "likes", "comments", "saves", "score")

    def __init__(self, subscriptions: list[str]) -> None:
        self.subscriptions = [url.strip() for url in subscriptions if url.strip()]

    def fetch(
        self,
        keywords: list[str],
        limit: int,
    ) -> list[dict]:
        candidates: list[dict] = []
        for subscription_url in self.subscriptions:
            feed = feedparser.parse(subscription_url)
            feed_title = self._feed_title(feed, subscription_url)
            for entry in feed.entries:
                article = self._normalize_entry(entry, feed_title, keywords)
                if article is None:
                    continue
                candidates.append(article)
                if len(candidates) >= limit:
                    return candidates
        return candidates

    def _normalize_entry(
        self,
        entry: object,
        feed_title: str,
        keywords: list[str],
    ) -> dict | None:
        title = str(getattr(entry, "title", "")).strip()
        url = str(getattr(entry, "link", "")).strip()
        if not title or not url:
            return None

        summary = self._clean_html_text(
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
        )
        source_host = urlparse(url).netloc or feed_title
        posted_at = self._format_published(entry)
        keyword_matches = self._keyword_match_count(title, summary, keywords)
        if keyword_matches == 0:
            return None

        text = self._build_text(
            title=title,
            url=url,
            source_host=source_host,
            feed_title=feed_title,
            posted_at=posted_at,
            summary=summary,
            keyword_matches=keyword_matches,
        )

        return {
            "title": title,
            "url": url,
            "source": feed_title,
            "text": text,
            "score": 0.0,
            "keyword_matches": keyword_matches,
            "likes": 0,
            "comments": 0,
            "saves": 0,
        }

    def _feed_title(self, feed: object, fallback_url: str) -> str:
        title = str(getattr(getattr(feed, "feed", None), "title", "")).strip()
        return title or urlparse(fallback_url).netloc or "FeedSubscription"

    def _build_text(
        self,
        title: str,
        url: str,
        source_host: str,
        feed_title: str,
        posted_at: str,
        summary: str,
        keyword_matches: int,
    ) -> str:
        detail_parts = [
            f"Title: {title}",
            f"Original article URL: {url}",
            f"Feed source: {feed_title}",
            f"Source host: {source_host}",
            f"Posted: {posted_at}",
            f"Keyword matches: {keyword_matches}",
        ]
        if summary:
            detail_parts.append(f"Feed summary: {summary}")
        return (
            ". ".join(detail_parts)
            + f". Hardcoded fields: {', '.join(self.ARTICLE_FIELDS)}."
        )

    def _keyword_match_count(self, title: str, summary: str, keywords: list[str]) -> int:
        haystack = f"{title} {summary}".lower()
        count = 0
        for keyword in keywords:
            normalized_keyword = keyword.strip().lower()
            if not normalized_keyword:
                continue
            if self._contains_keyword(haystack, normalized_keyword):
                count += 1
        return count

    def _contains_keyword(self, haystack: str, keyword: str) -> bool:
        parts = [part for part in re.split(r"[^a-z0-9]+", keyword) if part]
        if not parts:
            return False
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in parts) + r"\b"
        return bool(re.search(pattern, haystack))

    def _format_published(self, entry: object) -> str:
        published = str(
            getattr(entry, "published", "")
            or getattr(entry, "updated", "")
        ).strip()
        if not published:
            return "unknown"
        try:
            return parsedate_to_datetime(published).isoformat()
        except (TypeError, ValueError, OverflowError):
            return published

    def _clean_html_text(self, raw_text: object) -> str:
        if not raw_text:
            return ""
        text = unescape(str(raw_text))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500]
