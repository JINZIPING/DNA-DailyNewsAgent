from __future__ import annotations

import json
import os
from urllib import error, request


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self.model = model or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
        if not self.api_key:
            raise RuntimeError("Environment variable 'OPENROUTER_API_KEY' is required.")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, object]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "reasoning": {"enabled": False},
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 2400,
        }
        api_request = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Title": "DNA Daily News Agent",
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise RuntimeError(f"OpenRouter request failed: {error_body}") from exc
        except TimeoutError as exc:
            raise RuntimeError("OpenRouter request timed out.") from exc

        content = response_payload["choices"][0]["message"].get("content")
        if not content:
            raise RuntimeError("OpenRouter returned no visible content.")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenRouter returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("OpenRouter JSON response must be an object.")
        return result

