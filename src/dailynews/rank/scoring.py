from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
import re

from dailynews.core.models import NormalizedItem, RankedItem
from dailynews.rank.dedupe import dedupe_items


@dataclass(frozen=True, slots=True)
class HotWord:
    term: str
    weight: float


DEFAULT_HOT_WORDS = [
    HotWord("ai", 6),
    HotWord("agent", 6),
    HotWord("coding", 6),
    HotWord("model", 5),
    HotWord("research", 5),
    HotWord("eval", 5),
    HotWord("llm", 6),
    HotWord("openai", 8),
    HotWord("anthropic", 8),
    HotWord("claude", 8),
]

SOURCE_WEIGHTS = {
    "openai-news": 25,
    "anthropic-research-rsshub": 25,
    "sebastian-raschka": 20,
    "hugging-face-blog": 20,
    "latent-space": 18,
    "last-week-in-ai": 16,
    "ai-era-baai": 14,
    "agentmail-inbox": 12,
    "hacker-news-topstories": 10,
    "karpathy-twitter-rsshub": 10,
}


def rank_items(
    items: list[NormalizedItem],
    *,
    limit: int = 25,
    hot_words: list[HotWord] | None = None,
) -> list[RankedItem]:
    ranked = [
        score_item(item, hot_words=hot_words or DEFAULT_HOT_WORDS)
        for item in dedupe_items(items)
    ]
    return sorted(ranked, key=lambda item: item.score, reverse=True)[:limit]


def score_item(item: NormalizedItem, *, hot_words: list[HotWord]) -> RankedItem:
    score = 0.0
    reasons: list[str] = []

    recency = _recency_score(item.published_at)
    if recency:
        score += recency
        reasons.append(f"recency +{recency:g}")

    source_weight = SOURCE_WEIGHTS.get(item.source_id, _default_source_weight(item))
    if source_weight:
        score += source_weight
        reasons.append(f"source +{source_weight:g}")

    haystack = f"{item.title} {item.summary} {item.content} {' '.join(item.categories)}".lower()
    matches = [hot_word for hot_word in hot_words if _contains_keyword(haystack, hot_word.term)]
    if matches:
        hot_word_score = min(40, sum(match.weight for match in matches))
        score += hot_word_score
        terms = ", ".join(match.term for match in matches)
        reasons.append(f"hot words {terms} +{hot_word_score:g}")

    content_len = len(item.content or item.summary)
    if content_len > 1200:
        score += 12
        reasons.append("substantial content +12")
    elif content_len > 300:
        score += 8
        reasons.append("usable content +8")

    if item.url:
        score += 5
        reasons.append("source url +5")

    return RankedItem(item=item, score=score, reasons=reasons)


def _recency_score(value: str) -> float:
    if not value:
        return 0
    try:
        published = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours <= 24:
        return 30
    if age_hours <= 48:
        return 10
    return 0


def _default_source_weight(item: NormalizedItem) -> float:
    if item.source_type == "rss":
        return 14
    if item.source_type == "rsshub":
        return 12
    if item.source_type == "email":
        return 10
    return 5


def _contains_keyword(haystack: str, keyword: str) -> bool:
    normalized = keyword.strip().lower()
    if not normalized:
        return False
    pattern = r"\b" + re.escape(normalized).replace(r"\ ", r"\s+") + r"\b"
    return bool(re.search(pattern, haystack))
