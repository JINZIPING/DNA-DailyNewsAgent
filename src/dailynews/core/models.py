from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedItem:
    id: str
    source_id: str
    source_type: str
    source_name: str
    title: str
    url: str
    published_at: str
    summary: str
    content: str
    categories: list[str] = field(default_factory=list)
    fetched_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "summary": self.summary,
            "content": self.content,
            "categories": self.categories,
            "fetched_at": self.fetched_at,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizedItem":
        return cls(
            id=str(data.get("id", "")).strip(),
            source_id=str(data.get("source_id", "")).strip(),
            source_type=str(data.get("source_type", "")).strip(),
            source_name=str(data.get("source_name", "")).strip(),
            title=str(data.get("title", "")).strip(),
            url=str(data.get("url", "")).strip(),
            published_at=str(data.get("published_at", "")).strip(),
            summary=str(data.get("summary", "")).strip(),
            content=str(data.get("content", "")).strip(),
            categories=[str(item).strip() for item in data.get("categories", []) if str(item).strip()],
            fetched_at=str(data.get("fetched_at", "")).strip(),
            raw=dict(data.get("raw", {})),
        )


@dataclass(frozen=True, slots=True)
class RankedItem:
    item: NormalizedItem
    score: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = self.item.to_dict()
        payload["rank_score"] = self.score
        payload["rank_reasons"] = self.reasons
        return payload

