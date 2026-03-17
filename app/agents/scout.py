from __future__ import annotations

from app.config_loader import ToolInstanceConfig
from app.models.article import Article
from app.models.message import AgentMessage
from app.models.state import WorkflowState, WorkflowUpdate
from app.tools.news_fetch import FeedSubscriptionMethod, HackerNewsMethod

ARTICLE_FIELDS = ("title", "url", "source", "text", "likes", "comments", "saves", "score")

SCOUT_SYSTEM_PROMPT = """You are The Scout, the raw news collection agent.
Your job is to use the configured keywords as fetch queries, use only the
enabled fetch tools, collect candidate stories, and hand raw article data to
the Analyst without summarizing or rewriting the news.

Operating rules:
- fetch using only the configured keywords
- record popularity metadata from each fetch method when available
- collect enough candidates for the Analyst to rank later
- avoid inventing facts or editing article content
- preserve source URLs, source names, and popularity fields"""

def run(
    state: WorkflowState,
    max_articles: int,
    news_fetch_tools: dict[str, ToolInstanceConfig],
) -> WorkflowUpdate:
    keywords = _normalize_keywords(state.get("keywords", []))
    fetch_methods = state.get("fetch_methods", ["hacker_news"])
    scout_brief = _build_scout_brief(keywords, fetch_methods)

    fetched_articles = _fetch_articles(
        keywords,
        max_articles,
        fetch_methods,
        news_fetch_tools,
    )

    articles = Article.from_dicts(fetched_articles)

    messages = AgentMessage.from_dicts(state.get("messages", []))
    messages.append(
        AgentMessage(
            sender="Scout",
            recipient="Analyst",
            content=(
                f"Collected {len(articles)} raw articles for keywords [{', '.join(keywords)}] "
                f"using methods {', '.join(fetch_methods)} and hardcoded fields {', '.join(ARTICLE_FIELDS)}. "
                f"Scout brief: {scout_brief}"
            ),
        )
    )

    return {
        "raw_articles": Article.to_dicts(articles),
        "messages": AgentMessage.to_dicts(messages),
    }


def _fetch_articles(
    keywords: list[str],
    max_articles: int,
    fetch_methods: list[str],
    news_fetch_tools: dict[str, ToolInstanceConfig],
) -> list[dict]:
    articles: list[dict] = []
    for method_name in fetch_methods:
        tool = _build_fetch_tool(method_name, news_fetch_tools.get(method_name))
        if tool is None:
            continue
        articles.extend(tool.fetch(keywords, max_articles))
    return _deduplicate_articles(articles)[:max_articles]


def _build_fetch_tool(
    method_name: str,
    tool_config: ToolInstanceConfig | None,
):
    if method_name == "hacker_news":
        return HackerNewsMethod(base_url=tool_config.base_url if tool_config else None)
    if method_name == "feed_subscription":
        subscriptions = tool_config.subscriptions if tool_config else []
        return FeedSubscriptionMethod(subscriptions=subscriptions)
    return None


def _deduplicate_articles(articles: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for article in articles:
        key = (article["title"].strip().lower(), article["url"].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def _normalize_keywords(keywords: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        cleaned = keyword.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _build_scout_brief(
    keywords: list[str],
    fetch_methods: list[str],
) -> str:
    keyword_text = ", ".join(keywords) if keywords else "no keywords"
    methods_text = ", ".join(fetch_methods)
    return (
        f"Fetch with keywords [{keyword_text}]. "
        f"Use methods [{methods_text}] and preserve hardcoded fields [{', '.join(ARTICLE_FIELDS)}]."
    )
