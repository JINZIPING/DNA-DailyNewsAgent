from __future__ import annotations

from typing import TypedDict
from typing_extensions import NotRequired, Required

from app.models.article import ArticleRecord
from app.models.message import AgentMessageRecord


class WorkflowState(TypedDict):
    keywords: Required[list[str]]
    fetch_methods: Required[list[str]]
    revision_count: Required[int]
    messages: Required[list[AgentMessageRecord]]
    raw_articles: NotRequired[list[ArticleRecord]]
    filtered_articles: NotRequired[list[ArticleRecord]]
    draft_brief: NotRequired[str]
    final_brief_path: NotRequired[str]
    final_brief: NotRequired[str]
    editor_feedback: NotRequired[str]


class WorkflowUpdate(TypedDict, total=False):
    keywords: list[str]
    fetch_methods: list[str]
    revision_count: int
    messages: list[AgentMessageRecord]
    raw_articles: list[ArticleRecord]
    filtered_articles: list[ArticleRecord]
    draft_brief: str
    final_brief_path: str
    final_brief: str
    editor_feedback: str
