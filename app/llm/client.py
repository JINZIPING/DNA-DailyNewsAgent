from __future__ import annotations

import os

from openai import OpenAI

from app.config_loader import AppConfig


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        api_key = os.getenv(config.llm.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Environment variable '{config.llm.api_key_env}' is required for LLM usage."
            )
        self._client = OpenAI(api_key=api_key, base_url=config.llm.base_url)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self._config.llm.model,
            temperature=self._config.llm.temperature,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        )
        return response.output_text.strip()
