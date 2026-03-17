from __future__ import annotations

from app.llm.client import LLMClient
from app.models.article import Article
from app.models.message import AgentMessage
from app.models.state import WorkflowState, WorkflowUpdate


SYNTHESIZER_SYSTEM_PROMPT = """You are The Synthesizer, the drafting agent in a daily news workflow.
Write a concise Markdown news brief from the Analyst's filtered article set.
Synthesize overlapping information into cohesive paragraphs instead of just
listing isolated mini-summaries. Preserve uncertainty, stay factual, and keep
the brief readable for one daily skim.

Operating rules:
- write in clean Markdown with a title and short sections
- make the executive summary concrete and story-specific
- mention the actual ranked stories and their main claims in the summary
- end each news item with `[Source: SourceName](URL)`
- do not add a trailing Sources section
- do not add generic link phrases like `Read more here`
- write exactly one `###` subsection per filtered article
- do not merge multiple filtered articles into one subsection
- avoid vague summaries about "trends", "landscape", or "developments" unless tied to specific stories
- avoid hype, speculation, and invented details"""


def run(state: WorkflowState, llm_client: LLMClient) -> WorkflowUpdate:
    keywords = state.get("keywords", [])
    filtered_articles = Article.from_dicts(state.get("filtered_articles", []))
    if not filtered_articles:
        raise RuntimeError("No filtered articles are available for LLM synthesis.")

    analyst_handoff = _latest_message_for_sender(state, "Analyst")
    editor_feedback = state.get("editor_feedback", "").strip()
    draft_brief = llm_client.generate(
        SYNTHESIZER_SYSTEM_PROMPT,
        _build_llm_prompt(keywords, filtered_articles, analyst_handoff, editor_feedback),
    )

    messages = AgentMessage.from_dicts(state.get("messages", []))
    messages.append(
        AgentMessage(
            sender="Synthesizer",
            recipient="Editor",
            content=(
                f"Drafted a news brief from {len(filtered_articles)} filtered articles "
                f"for keywords [{', '.join(keywords)}]."
            ),
        )
    )

    return {
        "draft_brief": draft_brief,
        "messages": AgentMessage.to_dicts(messages),
    }


def _build_llm_prompt(
    keywords: list[str],
    articles: list[Article],
    analyst_handoff: str,
    editor_feedback: str,
) -> str:
    keyword_text = ", ".join(keywords) if keywords else "no keywords"
    feedback_section = f"\nEditor feedback: {editor_feedback}" if editor_feedback else ""
    handoff_section = f"\nAnalyst handoff: {analyst_handoff}" if analyst_handoff else ""
    article_context = _format_article_context(articles)
    return (
        f"Keywords: {keyword_text}"
        f"{handoff_section}"
        f"{feedback_section}\n\n"
        "Write a concise Markdown daily brief with:\n"
        "1. a title\n"
        "2. a short executive summary paragraph that names the actual ranked stories and states their concrete takeaways\n"
        f"3. exactly {len(articles)} short `###` subsections, one for each filtered article in rank order\n"
        "4. each news item must end with `[Source: SourceName](URL)` inline\n"
        "5. do not include a separate Sources section\n\n"
        "The executive summary must not be generic. It should summarize the specific articles provided below, not broad industry trends.\n"
        "Each subsection must cover only one article. Do not combine multiple articles into a shared subsection.\n\n"
        f"Articles:\n{article_context}"
    )


def _format_article_context(articles: list[Article]) -> str:
    return "\n\n".join(
        (
            f"Title: {article.title}\n"
            f"Source: {article.source}\n"
            f"URL: {article.url}\n"
            f"Popularity Score: {article.score:.2f}\n"
            f"Likes: {article.likes}\n"
            f"Comments: {article.comments}\n"
            f"Saves: {article.saves}\n"
            f"Text: {article.text}"
        )
        for article in articles
    )


def _latest_message_for_sender(state: WorkflowState, sender: str) -> str:
    messages = AgentMessage.from_dicts(state.get("messages", []))
    for message in reversed(messages):
        if message.sender == sender:
            return message.content
    return ""
