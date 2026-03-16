from __future__ import annotations

from app.models.article import Article
from app.models.message import AgentMessage
from app.models.state import WorkflowState, WorkflowUpdate

ANALYST_SYSTEM_PROMPT = """You are The Analyst, the ranking agent.
Your job is simple: remove duplicates from the Scout's raw article list and
rank the remaining articles by keyword match coverage first, then by recorded
popularity metrics."""


def run(state: WorkflowState, max_filtered_articles: int) -> WorkflowUpdate:
    raw_articles = Article.from_dicts(state.get("raw_articles", []))
    ranked_articles = sorted(
        deduplicate_articles(raw_articles),
        key=article_popularity,
        reverse=True,
    )
    filtered_articles = ranked_articles[:max_filtered_articles]

    messages = AgentMessage.from_dicts(state.get("messages", []))
    messages.append(
        AgentMessage(
            sender="Analyst",
            recipient="Synthesizer",
            content=(
                f"Reduced {len(raw_articles)} raw articles to {len(filtered_articles)} ranked articles. "
                "Analyst brief: removed duplicates, ranked higher keyword coverage first, then popularity."
            ),
        )
    )

    return {
        "filtered_articles": Article.to_dicts(filtered_articles),
        "messages": AgentMessage.to_dicts(messages),
    }


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    seen: set[tuple[str, str]] = set()
    unique: list[Article] = []
    for article in articles:
        key = (article.title.strip().lower(), article.url.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(article)
    return unique


def article_popularity(article: Article) -> tuple[int, float, int, int, int]:
    return (
        article.keyword_matches,
        article.score,
        article.likes,
        article.comments,
        article.saves,
    )
