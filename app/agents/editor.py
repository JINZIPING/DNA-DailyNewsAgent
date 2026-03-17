from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import TypedDict

from app.models.message import AgentMessage
from app.models.state import WorkflowState, WorkflowUpdate
from app.tools.email_sender import send_email
from app.tools.file_writer import write_markdown

EDITOR_SYSTEM_PROMPT = """You are The Editor / Supervisor in a daily news workflow.
Your job is to review the Synthesizer's draft against the configured keywords and basic
delivery standards. If the draft is incomplete, request a revision with clear,
actionable feedback. If it is good enough, save the final brief."""

MAX_REVISIONS = 2


class ReviewResult(TypedDict):
    approved: bool
    feedback: str
    summary: str


def run(
    state: WorkflowState,
    output_dir: str,
    recipient: str | None = None,
    email_api_key_env: str | None = None,
    email_sender_address: str | None = None,
) -> WorkflowUpdate:
    keywords = state.get("keywords", [])
    draft_brief = state.get("draft_brief", "").strip()
    revision_count = int(state.get("revision_count", 0))
    filtered_article_count = len(state.get("filtered_articles", []))

    messages = AgentMessage.from_dicts(state.get("messages", []))
    review = _review_draft(keywords, draft_brief, filtered_article_count)

    if not review["approved"] and revision_count < MAX_REVISIONS:
        feedback = review["feedback"]
        messages.append(
            AgentMessage(
                sender="Editor",
                recipient="Synthesizer",
                content=feedback,
            )
        )
        return {
            "editor_feedback": feedback,
            "revision_count": revision_count + 1,
            "messages": AgentMessage.to_dicts(messages),
        }
    if not review["approved"]:
        raise RuntimeError(
            "Editor rejected the draft after "
            f"{MAX_REVISIONS} revisions: {review['feedback']}"
        )

    review_summary = str(review["summary"])

    slug = "_".join(keyword.lower().replace(" ", "_") for keyword in keywords) or "news_brief"
    output_path = Path(output_dir) / f"{date.today().isoformat()}_{slug}.md"
    saved_path = write_markdown(str(output_path), draft_brief)

    if recipient:
        send_email(
            recipient=recipient,
            subject=f"Daily News Brief: {', '.join(keywords)}",
            body=draft_brief,
            api_key_env=email_api_key_env,
            sender_email=email_sender_address,
        )

    messages.append(
        AgentMessage(
            sender="Editor",
            recipient="User",
            content=(
                f"Approved and saved final brief to {saved_path}. "
                f"Review summary: {review_summary}"
            ),
        )
    )

    return {
        "final_brief_path": saved_path,
        "final_brief": draft_brief,
        "editor_feedback": "",
        "messages": AgentMessage.to_dicts(messages),
    }


def _review_draft(keywords: list[str], draft_brief: str, filtered_article_count: int) -> ReviewResult:
    failures: list[str] = []
    normalized = draft_brief.strip()
    lower = normalized.lower()

    if len(normalized) < 300:
        failures.append("expand the brief beyond a minimal stub")
    if not normalized.startswith("# "):
        failures.append("add a Markdown H1 title")
    if "## Executive Summary" not in normalized:
        failures.append("include an Executive Summary section")
    if "## Sources" in normalized:
        failures.append("remove the trailing Sources section")
    if keywords and not any(keyword.lower() in lower for keyword in keywords):
        failures.append("mention at least one configured keyword explicitly in the brief")
    if filtered_article_count > 0 and _count_markdown_links(normalized) < filtered_article_count:
        failures.append("cite each filtered article inline with a markdown source link")
    if filtered_article_count > 0 and normalized.count("[Source:") < filtered_article_count:
        failures.append("end each news item with `[Source: SourceName](URL)`")
    subsection_count = _count_level_three_sections(normalized)
    if filtered_article_count > 0 and subsection_count != filtered_article_count:
        failures.append(
            f"write exactly {filtered_article_count} `###` news subsections, one for each filtered article"
        )
    if filtered_article_count > 0 and not _all_subsections_have_source_link(normalized):
        failures.append("ensure every `###` news subsection ends with an inline markdown source link")
    if _count_paragraphs(normalized) < 3:
        failures.append("add more synthesis paragraphs instead of a thin outline")

    approved = not failures
    if approved:
        return {
            "approved": True,
            "feedback": "",
            "summary": "draft passed title, structure, keyword coverage, and citation checks",
        }

    return {
        "approved": False,
        "feedback": (
            "Revise the brief. "
            "Editor review found these issues: "
            + "; ".join(failures)
            + ". Keep the brief factual and preserve source links."
        ),
        "summary": "draft needs revision",
    }


def _count_markdown_links(text: str) -> int:
    return len(re.findall(r"\[[^\]]+\]\([^)]+\)", text))


def _count_level_three_sections(text: str) -> int:
    return len(re.findall(r"(?m)^###\s+", text))


def _all_subsections_have_source_link(text: str) -> bool:
    sections = re.split(r"(?m)^###\s+", text)
    subsection_bodies = sections[1:]
    if not subsection_bodies:
        return False
    for body in subsection_bodies:
        if "[Source:" not in body:
            return False
    return True


def _count_paragraphs(text: str) -> int:
    count = 0
    for block in (block.strip() for block in text.split("\n\n")):
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        content_lines = [
            line for line in lines if not line.startswith("#") and not line.startswith("- ")
        ]
        if content_lines:
            count += 1
    return count
