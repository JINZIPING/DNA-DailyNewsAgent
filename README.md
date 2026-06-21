# DNA Daily News Agent CLI

A `dailynews` command-line tool for collecting AI news, ranking recent stories, summarizing them with an LLM, rendering an email, and sending it through Resend.

The v1 prototype is kept at [`JINZIPING/DNA-DailyNewsAgent-V1`](https://github.com/JINZIPING/DNA-DailyNewsAgent-V1).

## Pipeline

```text
collect sources -> normalize -> dedupe -> rank -> summarize -> render email -> send
```

There is no database in the current version. Each run writes JSON/HTML artifacts under the output path you choose, which fits the current one-shot daily brief workflow.

## Setup

Install the project as a local CLI tool with `uv`:

```bash
uv tool install --editable .
dailynews --help
```

If `dailynews` is not found after installation, run `uv tool update-shell`, restart the shell, and try again.

Create a local environment file:

```bash
cp .env.example .env
```

Required environment variables:

```text
RESEND_API_KEY=
AGENTMAIL_API_KEY=
AGENTMAIL_INBOX_ID=
RSSHUB_GITHUB_ACCESS_TOKEN=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
DAILYNEWS_RECIPIENT=
```

`RSSHUB_GITHUB_ACCESS_TOKEN` is passed into the one-time RSSHub Docker container as `GITHUB_ACCESS_TOKEN` for GitHub routes.

## Run Locally

Prepare ranked stories:

```bash
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
```

Generate and send the email:

```bash
dailynews summarize --in output/ranked.json --out output/brief.json --max-items 7
dailynews render-email --in output/brief.json --out output/brief.html
dailynews send-email --brief output/brief.json --html output/brief.html --to "$DAILYNEWS_RECIPIENT"
```

Useful source checks:

```bash
dailynews agentmail-fetch --limit 25 --metadata-only
dailynews rss-fetch --url https://openai.com/news/rss.xml --limit 10
dailynews rsshub-fetch rsshub://anthropic/research --limit 10
```

## Configuration

Runtime sources live in [`config/sources.json`](./config/sources.json).

Supported source types:

- `rss`: direct RSS or Atom feed.
- `rsshub`: starts a temporary local RSSHub Docker container and fetches the route.
- `agentmail`: reads inbound newsletter messages from AgentMail.

Human-readable source notes live in [`docs/sources.md`](./docs/sources.md).

Ranking hot words live in [`config/ranking.json`](./config/ranking.json). Increase a term's weight to push matching stories higher.

AgentMail sources can define `exclude_subject_prefixes` to filter signup, verification, welcome, and test messages before ranking.

## Agent Skill

Agent-facing CLI instructions live in [`skills/dailynews/SKILL.md`](./skills/dailynews/SKILL.md).

Use this file when you want another AI agent to operate the project without rediscovering the workflow. It tells the agent how to run the daily brief pipeline, check individual sources, preserve the source/ranking config boundaries, and report results without exposing secrets.

## GitHub Action

Workflow: [`.github/workflows/daily-brief.yml`](./.github/workflows/daily-brief.yml)

Triggers:

- Daily at `00:00 UTC`, which is `08:00` China Standard Time.
- Manual `workflow_dispatch`.
- Pull requests targeting `main`.

PR runs execute the same prepare, summarize, render, validate, and email-send path. Secret-backed PR verification only runs for branches inside this repository; fork PRs are skipped.

Required Actions secrets:

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

The workflow uploads generated artifacts from `output/` for seven days.

## Project Layout

```text
src/dailynews/
  core/          pipeline policy and shared models
  ingest/        RSS, RSSHub, AgentMail collection
  normalize/     source records to common item schema
  rank/          dedupe and scoring
  summarize/     OpenRouter-backed brief generation
  publish/       email rendering and Resend delivery
  cli.py         command entrypoint

config/
  sources.json   runtime source list
  ranking.json   hot-word ranking config

docs/
  sources.md     human-editable source registry

skills/
  dailynews/      agent-facing CLI instructions
```
