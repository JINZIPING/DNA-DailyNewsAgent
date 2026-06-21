from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys

from dailynews.core.models import NormalizedItem
from dailynews.ingest.agentmail import fetch_messages
from dailynews.ingest.rss import fetch_rss_items
from dailynews.ingest.rsshub import (
    DEFAULT_RSSHUB_IMAGE,
    DEFAULT_RSSHUB_PORT,
    rsshub_route_url,
    temporary_rsshub,
)
from dailynews.normalize.items import normalize_records


@dataclass(frozen=True, slots=True)
class SourceConfig:
    id: str
    type: str
    name: str
    url: str = ""
    enabled: bool = True
    limit: int = 50
    timeout: int = 30
    exclude_subject_prefixes: tuple[str, ...] = ()


def load_sources(path: str) -> list[SourceConfig]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
    return [
        SourceConfig(
            id=str(item.get("id", "")).strip(),
            type=str(item.get("type", "")).strip(),
            name=str(item.get("name", "")).strip(),
            url=str(item.get("url", "")).strip(),
            enabled=bool(item.get("enabled", True)),
            limit=int(item.get("limit", 50)),
            timeout=int(item.get("timeout", 30)),
            exclude_subject_prefixes=tuple(
                str(prefix).strip().lower()
                for prefix in item.get("exclude_subject_prefixes", [])
                if str(prefix).strip()
            ),
        )
        for item in raw_sources
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]


def collect_sources(
    sources: list[SourceConfig],
    *,
    rsshub_image: str = DEFAULT_RSSHUB_IMAGE,
    rsshub_port: int = DEFAULT_RSSHUB_PORT,
) -> list[NormalizedItem]:
    enabled = [source for source in sources if source.enabled]
    items: list[NormalizedItem] = []

    for source in enabled:
        if source.type == "rsshub":
            continue
        try:
            items.extend(_collect_source(source))
        except Exception as exc:
            _report_source_error(source, exc)

    rsshub_sources = [source for source in enabled if source.type == "rsshub"]
    if rsshub_sources:
        try:
            with temporary_rsshub(image=rsshub_image, port=rsshub_port) as base_url:
                for source in rsshub_sources:
                    try:
                        items.extend(_collect_rsshub_source(source, base_url))
                    except Exception as exc:
                        _report_source_error(source, exc)
        except Exception as exc:
            for source in rsshub_sources:
                _report_source_error(source, exc)

    return items


def _collect_source(source: SourceConfig) -> list[NormalizedItem]:
    if source.type == "rss":
        records = [
            item.to_dict()
            for item in fetch_rss_items(source.url, limit=source.limit, timeout=source.timeout)
        ]
        return normalize_records(records, source_id=source.id, source_type=source.type)

    if source.type == "agentmail":
        response = fetch_messages(limit=source.limit)
        response = filter_agentmail_response(response, source.exclude_subject_prefixes)
        return normalize_records(response, source_id=source.id, source_type=source.type)

    raise RuntimeError(f"Unsupported source type '{source.type}'.")


def _collect_rsshub_source(source: SourceConfig, base_url: str) -> list[NormalizedItem]:
    url = rsshub_route_url(source.url, base_url=base_url)
    records = [
        item.to_dict()
        for item in fetch_rss_items(url, limit=source.limit, timeout=source.timeout)
    ]
    return normalize_records(records, source_id=source.id, source_type=source.type)


def _report_source_error(source: SourceConfig, error: Exception) -> None:
    print(f"Source '{source.id}' failed: {error}", file=sys.stderr)


def filter_agentmail_response(
    response: dict[str, object],
    excluded_subject_prefixes: tuple[str, ...],
) -> dict[str, object]:
    messages = response.get("messages", [])
    if not isinstance(messages, list):
        return response

    filtered = [
        message
        for message in messages
        if isinstance(message, dict)
        and not _subject_has_prefix(message.get("subject"), excluded_subject_prefixes)
    ]
    return {**response, "messages": filtered, "count": len(filtered)}


def _subject_has_prefix(subject: object, prefixes: tuple[str, ...]) -> bool:
    normalized = str(subject or "").strip().lower()
    return any(normalized.startswith(prefix) for prefix in prefixes)
