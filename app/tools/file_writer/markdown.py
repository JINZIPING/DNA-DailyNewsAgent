from __future__ import annotations

from pathlib import Path


def write_markdown(path: str, content: str) -> str:
    normalized_content = _normalize_markdown(content)
    output_path = _normalize_output_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized_content, encoding="utf-8")
    return str(output_path.resolve())


def _normalize_output_path(path: str) -> Path:
    output_path = Path(path)
    if output_path.suffix.lower() != ".md":
        output_path = output_path.with_suffix(".md")
    return output_path


def _normalize_markdown(content: str) -> str:
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        raise ValueError("Markdown content cannot be empty.")
    return normalized + "\n"
