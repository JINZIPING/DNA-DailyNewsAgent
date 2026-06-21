---
name: dailynews
description: Use when a user wants to run, verify, or explain the DNA Daily News Agent CLI for collecting AI news, ranking stories, generating a daily brief, rendering HTML email, or sending the brief through Resend.
---

# DNA Daily News Agent CLI

Use the installed `dailynews` CLI. Install it with `uv tool install --editable .` when needed. Do not use `python`, `pip`, or `poetry` directly in this repo.

## First Checks

Before running the pipeline:

- Read `README.md` for the current workflow.
- Check `.env.example` for required environment variables.
- Never print secrets from `.env`.
- Prefer `dailynews ...` commands after installing the tool.
- If `dailynews` is not found, run `uv tool update-shell`, restart the shell, and try again.
- Use `config/sources.json` for runtime sources.
- Use `config/ranking.json` for ranking hot words.

Required environment variables for a full email run:

```text
RESEND_API_KEY
AGENTMAIL_API_KEY
AGENTMAIL_INBOX_ID
RSSHUB_GITHUB_ACCESS_TOKEN
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
OPENROUTER_MODEL
DAILYNEWS_RECIPIENT
```

## Normal Daily Brief Flow

Run these commands when the user asks for a local end-to-end daily brief:

```bash
uv tool install --editable .
dailynews prepare \
  --sources config/sources.json \
  --hot-words config/ranking.json \
  --since-hours 24 \
  --fallback-hours 72 \
  --min-items 3 \
  --min-sources 2 \
  --max-per-source 3 \
  --limit 7 \
  --out output/ranked.json
dailynews summarize --in output/ranked.json --out output/brief.json --max-items 7
dailynews render-email --in output/brief.json --out output/brief.html
dailynews send-email --brief output/brief.json --html output/brief.html --to "$DAILYNEWS_RECIPIENT"
```

The selection policy is intentional: prefer the last 24 hours; if that cannot produce at least 3 stories across at least 2 sources, fallback to 72 hours; cap each source at 3 stories; send 3-7 stories when possible.

## Source Checks

Use focused checks before a full run when debugging source problems:

```bash
dailynews agentmail-fetch --limit 25 --metadata-only
dailynews rss-fetch --url https://openai.com/news/rss.xml --limit 10
dailynews rsshub-fetch rsshub://anthropic/research --limit 10
```

RSSHub routes start a temporary local Docker container. GitHub RSSHub routes need `RSSHUB_GITHUB_ACCESS_TOKEN`; the CLI maps it into the container as `GITHUB_ACCESS_TOKEN`.

## Editing Guidance

When changing behavior:

- Keep source fetching, ranking, summarization, rendering, and sending decoupled.
- Put new runtime feeds in `config/sources.json`.
- Mirror human-readable source notes in `docs/sources.md`.
- Put ranking preference changes in `config/ranking.json`, not in code.
- Keep the CLI output artifacts JSON/HTML based unless the user explicitly asks for storage.

## GitHub Action

The workflow at `.github/workflows/daily-brief.yml` runs the same prepare, summarize, render, validate, and send path:

- Scheduled daily at `00:00 UTC`, which is `08:00` China Standard Time.
- Manually via `workflow_dispatch`.
- On pull requests targeting `main`.

For workflow fixes, preserve PR email verification unless the user explicitly changes that requirement.

## Reporting

When reporting results to the user:

- Say how many ranked stories were produced and how many sources they came from.
- Mention whether the run used the 24-hour window or the 72-hour fallback if known.
- If email was sent, report the Resend response id.
- If a source failed, name the source and keep the summary concise.
