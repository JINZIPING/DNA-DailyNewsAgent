from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from app.config_loader import load_app_config
from app.graph.workflow import build_workflow
from app.models.state import WorkflowState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DNA Daily News Agent workflow.")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file.")
    return parser.parse_args()


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"))
    try:
        args = parse_args()
        config = load_app_config(args.config)
        workflow = build_workflow(config)

        enabled_fetch_methods = [
            tool.name
            for tool in config.tools.news_fetch.tools.values()
            if tool.enabled
        ]

        initial_state: WorkflowState = {
            "keywords": list(config.scraping.keywords),
            "fetch_methods": enabled_fetch_methods,
            "revision_count": 0,
            "messages": [],
        }
        result = workflow.invoke(initial_state)

        print("=== Final State ===")
        print(json.dumps(result, indent=2))
    except RuntimeError as error:
        raise SystemExit(f"Error: {error}") from error


if __name__ == "__main__":
    main()
