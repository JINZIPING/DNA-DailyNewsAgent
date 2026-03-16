from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
from urllib.parse import urlparse

import httpx


class HackerNewsMethod:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    ARTICLE_FIELDS = ("title", "url", "source", "text", "keyword_matches", "likes", "comments", "saves", "score")

    def fetch(
        self,
        keywords: list[str],
        limit: int,
    ) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.BASE_URL}/topstories.json")
                response.raise_for_status()
                story_ids = response.json()

                candidates: list[dict] = []
                for story_id in story_ids[: min(50, max(limit * 8, 20))]:
                    item_response = client.get(f"{self.BASE_URL}/item/{story_id}.json")
                    item_response.raise_for_status()
                    item = item_response.json()
                    if not item or item.get("type") != "story" or not item.get("title"):
                        continue

                    article = self._normalize_item(item, keywords)
                    if article:
                        candidates.append(article)
                    if len(candidates) >= limit:
                        break
                return candidates
        except httpx.HTTPError:
            return []

    def _normalize_item(
        self,
        item: dict,
        keywords: list[str],
    ) -> dict | None:
        title = str(item.get("title", "")).strip()
        item_id = int(item.get("id", 0))
        url = str(item.get("url") or f"https://news.ycombinator.com/item?id={item_id}")
        discussion_url = f"https://news.ycombinator.com/item?id={item_id}"
        source_host = urlparse(url).netloc or "news.ycombinator.com"
        author = str(item.get("by", "unknown")).strip() or "unknown"
        posted_at = self._format_posted_time(item.get("time"))
        story_text = self._clean_story_text(item.get("text"))
        likes = int(item.get("score", 0))
        comments = int(item.get("descendants", 0))
        saves = 0
        popularity_score = self._popularity_score(likes, comments, saves)
        keyword_matches = self._keyword_match_count(title, story_text, keywords)
        text = self._build_text(
            title=title,
            url=url,
            discussion_url=discussion_url,
            source_host=source_host,
            author=author,
            posted_at=posted_at,
            story_text=story_text,
            keyword_matches=keyword_matches,
            likes=likes,
            comments=comments,
            saves=saves,
        )

        if keyword_matches == 0:
            return None

        return {
            "title": title,
            "url": url,
            "source": "HackerNews",
            "text": text,
            "score": popularity_score,
            "keyword_matches": keyword_matches,
            "likes": likes,
            "comments": comments,
            "saves": saves,
        }

    def _build_text(
        self,
        title: str,
        url: str,
        discussion_url: str,
        source_host: str,
        author: str,
        posted_at: str,
        story_text: str,
        keyword_matches: int,
        likes: int,
        comments: int,
        saves: int,
    ) -> str:
        detail_parts = [
            f"Title: {title}",
            f"Original article URL: {url}",
            f"Source host: {source_host}",
            f"Hacker News discussion: {discussion_url}",
            f"Submitted by: {author}",
            f"Posted: {posted_at}",
            f"Keyword matches: {keyword_matches}",
            (
                f"Popularity snapshot: {likes} likes, {comments} comments, {saves} saves"
            ),
        ]
        if story_text:
            detail_parts.append(f"Hacker News post text: {story_text}")
        return (
            ". ".join(detail_parts)
            + f". Hardcoded fields: {', '.join(self.ARTICLE_FIELDS)}."
        )

    def _popularity_score(self, likes: int, comments: int, saves: int) -> float:
        return float(likes + comments + saves)

    def _keyword_match_count(self, title: str, story_text: str, keywords: list[str]) -> int:
        haystack = f"{title} {story_text}".lower()
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

    def _format_posted_time(self, raw_timestamp: object) -> str:
        if not raw_timestamp:
            return "unknown"
        posted = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc)
        return posted.isoformat()

    def _clean_story_text(self, raw_text: object) -> str:
        if not raw_text:
            return ""
        text = unescape(str(raw_text))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:400]
