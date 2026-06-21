from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from dailynews.core.models import NormalizedItem
from dailynews.llm.openrouter import OpenRouterClient


SYSTEM_PROMPT = """You are the editor of DNA Daily Brief.
Write a concise, factual English news brief from only the supplied story data.
Do not invent facts, numbers, entities, quotes, dates, or implications.
Return valid JSON only. Do not include Markdown fences.

Required JSON shape:
{
  "headline": "short concrete headline",
  "executive_summary": "2-3 sentences covering the most important stories",
  "stories": [
    {
      "id": "exact supplied story id",
      "summary": "1-2 factual sentences",
      "why_it_matters": "one concise sentence grounded in the supplied content"
    }
  ]
}

Include every supplied story exactly once and preserve each supplied id exactly."""


@dataclass(frozen=True, slots=True)
class BriefStory:
    id: str
    title: str
    summary: str
    why_it_matters: str
    source_name: str
    source_url: str
    published_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "published_at": self.published_at,
        }


@dataclass(frozen=True, slots=True)
class DailyBrief:
    headline: str
    executive_summary: str
    stories: list[BriefStory]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "stories": [story.to_dict() for story in self.stories],
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DailyBrief":
        return cls(
            headline=str(data.get("headline", "DNA Daily Brief")).strip(),
            executive_summary=str(data.get("executive_summary", "")).strip(),
            stories=[BriefStory(**story) for story in data.get("stories", [])],
            generated_at=str(data.get("generated_at", "")).strip(),
        )


def summarize_ranked_items(
    records: list[dict[str, Any]],
    client: OpenRouterClient,
    *,
    max_items: int = 8,
) -> DailyBrief:
    selected = [NormalizedItem.from_dict(record) for record in records[:max_items]]
    if not selected:
        raise RuntimeError("No ranked items are available to summarize.")

    context = [
        {
            "id": item.id,
            "title": item.title,
            "source": item.source_name,
            "published_at": item.published_at,
            "summary": item.summary,
            "content": item.content[:5000],
        }
        for item in selected
    ]
    response = client.generate_json(
        SYSTEM_PROMPT,
        "Create today's brief from these ranked stories:\n" + json.dumps(context, ensure_ascii=False),
    )

    generated_by_id = {
        str(story.get("id", "")): story
        for story in response.get("stories", [])
        if isinstance(story, dict)
    }
    stories: list[BriefStory] = []
    for item in selected:
        generated = generated_by_id.get(item.id, {})
        stories.append(
            BriefStory(
                id=item.id,
                title=item.title,
                summary=str(generated.get("summary") or item.summary or item.content[:500]).strip(),
                why_it_matters=str(generated.get("why_it_matters", "")).strip(),
                source_name=item.source_name,
                source_url=item.url,
                published_at=item.published_at,
            )
        )

    return DailyBrief(
        headline=str(response.get("headline", "DNA Daily Brief")).strip(),
        executive_summary=str(response.get("executive_summary", "")).strip(),
        stories=stories,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

