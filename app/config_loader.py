from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class LLMConfig:
    base_url: str | None
    api_key_env: str
    model: str
    temperature: float


@dataclass(slots=True)
class WorkflowConfig:
    output_dir: str
    max_articles: int
    max_filtered_articles: int


@dataclass(slots=True)
class ScrapingConfig:
    keywords: list[str]


@dataclass(slots=True)
class ToolInstanceConfig:
    name: str
    enabled: bool
    base_url: str | None
    api_key_env: str | None
    default_recipient: str = ""
    sender_email: str = ""


@dataclass(slots=True)
class ToolDomainConfig:
    tools: dict[str, ToolInstanceConfig]


@dataclass(slots=True)
class ToolsConfig:
    news_fetch: ToolDomainConfig
    file_writer: ToolDomainConfig
    email_sender: ToolDomainConfig


@dataclass(slots=True)
class AppConfig:
    llm: LLMConfig
    workflow: WorkflowConfig
    scraping: ScrapingConfig
    tools: ToolsConfig


def load_app_config(path: str = "config.yaml") -> AppConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    llm_payload = payload.get("model_api", {})
    workflow_payload = payload.get("workflow", {})
    scraping_payload = payload.get("scraping", {})
    tools_payload = payload.get("tools", {})

    keywords = [str(item) for item in scraping_payload.get("keywords", [])]
    if len(keywords) > 3:
        raise ValueError("scraping.keywords supports at most 3 keywords.")

    return AppConfig(
        llm=LLMConfig(
            base_url=(str(llm_payload["base_url"]) if llm_payload.get("base_url") else None),
            api_key_env=str(llm_payload.get("api_key_env", "OPENAI_API_KEY")),
            model=str(llm_payload.get("model", "gpt-4o-mini")),
            temperature=float(llm_payload.get("temperature", 0.4)),
        ),
        workflow=WorkflowConfig(
            output_dir=str(workflow_payload.get("output_dir", "outputs")),
            max_articles=int(workflow_payload.get("max_articles", 6)),
            max_filtered_articles=int(workflow_payload.get("max_filtered_articles", 3)),
        ),
        scraping=ScrapingConfig(
            keywords=keywords,
        ),
        tools=ToolsConfig(
            news_fetch=_tool_domain_config(_section(tools_payload, "news_fetch")),
            file_writer=_tool_domain_config(_section(tools_payload, "file_writer")),
            email_sender=_tool_domain_config(_section(tools_payload, "email_sender")),
        ),
    )


def _tool_domain_config(payload: dict) -> ToolDomainConfig:
    tools_payload = _section(payload, "tools")
    tools = {
        tool_key: ToolInstanceConfig(
            name=str(tool_payload.get("name", tool_key)),
            enabled=bool(tool_payload.get("enabled", False)),
            base_url=_optional_str(tool_payload, "base_url"),
            api_key_env=_optional_str(tool_payload, "api_key_env"),
            default_recipient=str(tool_payload.get("default_recipient", "")),
            sender_email=str(tool_payload.get("sender_email", "")),
        )
        for tool_key, tool_payload in tools_payload.items()
    }
    return ToolDomainConfig(tools=tools)


def _section(payload: dict, key: str) -> dict:
    return payload.get(key, {})


def _optional_str(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value else None
