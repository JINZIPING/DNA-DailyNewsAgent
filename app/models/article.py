from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, NotRequired, Required, TypedDict


class ArticleRecord(TypedDict, total=False):
    title: Required[str]
    url: Required[str]
    source: Required[str]
    text: Required[str]
    score: NotRequired[float]
    keyword_matches: NotRequired[int]
    likes: NotRequired[int]
    comments: NotRequired[int]
    saves: NotRequired[int]


@dataclass(slots=True, frozen=True)
class Article:
    title: str
    url: str
    source: str
    text: str
    score: float = 0.0
    keyword_matches: int = 0
    likes: int = 0
    comments: int = 0
    saves: int = 0

    def to_dict(self) -> ArticleRecord:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "text": self.text,
            "score": self.score,
            "keyword_matches": self.keyword_matches,
            "likes": self.likes,
            "comments": self.comments,
            "saves": self.saves,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Article":
        return cls(
            title=_required_text(data, "title"),
            url=_required_text(data, "url"),
            source=_required_text(data, "source"),
            text=_required_text(data, "text"),
            score=float(data.get("score", 0.0)),
            keyword_matches=int(data.get("keyword_matches", 0)),
            likes=int(data.get("likes", 0)),
            comments=int(data.get("comments", 0)),
            saves=int(data.get("saves", 0)),
        )

    @classmethod
    def from_dicts(cls, items: Iterable[Mapping[str, object]]) -> list["Article"]:
        return [cls.from_dict(item) for item in items]

    @staticmethod
    def to_dicts(items: Iterable["Article"]) -> list[ArticleRecord]:
        return [item.to_dict() for item in items]


def _required_text(data: Mapping[str, object], key: str) -> str:
    value = str(data[key]).strip()
    if not value:
        raise ValueError(f"Article field '{key}' cannot be empty.")
    return value
