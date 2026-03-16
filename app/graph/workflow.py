from __future__ import annotations

from typing import cast

from langgraph.graph import END, START, StateGraph

from app.agents import analyst, editor, scout, synthesizer
from app.config_loader import AppConfig
from app.llm.client import LLMClient
from app.models.state import WorkflowState


def build_workflow(config: AppConfig):
    llm_client = LLMClient(config)
    email_tool = next(
        (
            tool
            for tool in config.tools.email_sender.tools.values()
            if tool.enabled
        ),
        None,
    )
    email_recipient = email_tool.default_recipient if email_tool and email_tool.default_recipient else None
    email_api_key_env = email_tool.api_key_env if email_tool else None
    email_sender_address = email_tool.sender_email if email_tool else None

    graph = StateGraph(WorkflowState)
    graph.add_node("scout", lambda state: _run_scout(cast(WorkflowState, state), config))
    graph.add_node("analyst", lambda state: _run_analyst(cast(WorkflowState, state), config))
    graph.add_node("synthesizer", lambda state: _run_synthesizer(cast(WorkflowState, state), llm_client))
    graph.add_node(
        "editor",
        lambda state: _run_editor(
            cast(WorkflowState, state),
            config,
            email_recipient,
            email_api_key_env,
            email_sender_address,
        ),
    )

    graph.add_edge(START, "scout")
    graph.add_edge("scout", "analyst")
    graph.add_edge("analyst", "synthesizer")
    graph.add_edge("synthesizer", "editor")
    graph.add_conditional_edges(
        "editor",
        _next_step_after_editor,
        {
            "synthesizer": "synthesizer",
            "end": END,
        },
    )

    return graph.compile()


def _next_step_after_editor(state: WorkflowState) -> str:
    return "end" if state.get("final_brief_path") else "synthesizer"


def _run_scout(state: WorkflowState, config: AppConfig):
    return scout.run(state, config.workflow.max_articles)


def _run_analyst(state: WorkflowState, config: AppConfig):
    return analyst.run(state, config.workflow.max_filtered_articles)


def _run_synthesizer(state: WorkflowState, llm_client: LLMClient):
    return synthesizer.run(state, llm_client)


def _run_editor(
    state: WorkflowState,
    config: AppConfig,
    email_recipient: str | None,
    email_api_key_env: str | None,
    email_sender_address: str | None,
):
    return editor.run(
        state,
        config.workflow.output_dir,
        email_recipient,
        email_api_key_env,
        email_sender_address,
    )
