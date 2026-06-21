## Python Tooling

Use `uv` for all Python commands in this project.

Do not use:
- `python`
- `pip`
- `poetry`

Use:
```bash
uv sync
uv add ...
uv run python ...
uv run pytest