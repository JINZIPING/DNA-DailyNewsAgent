from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import Counter

from dailynews.core.models import NormalizedItem, RankedItem
from dailynews.rank.scoring import HotWord, rank_items


def filter_recent(
    items: list[NormalizedItem],
    *,
    since_hours: int,
    now: datetime | None = None,
) -> list[NormalizedItem]:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(hours=since_hours)
    recent: list[NormalizedItem] = []
    for item in items:
        published_at = _parse_datetime(item.published_at or item.fetched_at)
        if published_at and published_at >= cutoff:
            recent.append(item)
    return recent


def prepare_items(
    items: list[NormalizedItem],
    *,
    since_hours: int,
    fallback_hours: int = 72,
    min_items: int = 3,
    min_sources: int = 2,
    limit: int,
    max_per_source: int = 3,
    hot_words: list[HotWord] | None = None,
) -> list[RankedItem]:
    preferred = _rank_and_select(
        filter_recent(items, since_hours=since_hours),
        limit=limit,
        max_per_source=max_per_source,
        min_sources=min_sources,
        hot_words=hot_words,
    )
    if _meets_minimums(preferred, min_items=min_items, min_sources=min_sources):
        return preferred

    fallback = _rank_and_select(
        filter_recent(items, since_hours=fallback_hours),
        limit=limit,
        max_per_source=max_per_source,
        min_sources=min_sources,
        hot_words=hot_words,
    )
    return fallback


def _rank_and_select(
    items: list[NormalizedItem],
    *,
    limit: int,
    max_per_source: int,
    min_sources: int,
    hot_words: list[HotWord] | None,
) -> list[RankedItem]:
    ranked = rank_items(items, limit=max(len(items), limit), hot_words=hot_words)
    selected: list[RankedItem] = []
    selected_ids: set[str] = set()
    source_counts: Counter[str] = Counter()

    source_leaders: list[RankedItem] = []
    seen_sources: set[str] = set()
    for ranked_item in ranked:
        source_id = ranked_item.item.source_id
        if source_id not in seen_sources:
            seen_sources.add(source_id)
            source_leaders.append(ranked_item)
        if len(source_leaders) >= min_sources:
            break

    for ranked_item in source_leaders:
        _add_selected(ranked_item, selected, selected_ids, source_counts)

    for ranked_item in ranked:
        if len(selected) >= limit:
            break
        source_id = ranked_item.item.source_id
        if ranked_item.item.id in selected_ids or source_counts[source_id] >= max_per_source:
            continue
        _add_selected(ranked_item, selected, selected_ids, source_counts)

    return sorted(selected, key=lambda item: item.score, reverse=True)


def _add_selected(
    ranked_item: RankedItem,
    selected: list[RankedItem],
    selected_ids: set[str],
    source_counts: Counter[str],
) -> None:
    selected.append(ranked_item)
    selected_ids.add(ranked_item.item.id)
    source_counts[ranked_item.item.source_id] += 1


def _meets_minimums(
    items: list[RankedItem],
    *,
    min_items: int,
    min_sources: int,
) -> bool:
    source_count = len({item.item.source_id for item in items})
    return len(items) >= min_items and source_count >= min_sources


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
