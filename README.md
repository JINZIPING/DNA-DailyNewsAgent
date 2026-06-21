# DNA Daily News Agent v2

A daily news intelligence tool designed around one reusable core and three ways to run it:

- **CLI** for local use, scripting, and development.
- **GitHub Action** for scheduled automated briefs.
- **Skill** for agent-facing usage instructions.

The v1 prototype is kept under [`reference/v1`](./reference/v1).

## Goal

Build a reliable pipeline that can fetch news, normalize sources, rank stories, generate grounded briefs, verify outputs, and publish results.

```text
ingest -> normalize -> enrich -> cluster -> rank -> synthesize -> verify -> publish
```

## Planned Interfaces

### CLI

```bash
dailynews run --config config.yaml
dailynews fetch --topic "ai agents"
dailynews brief --topic "ai coding" --format markdown
dailynews verify --brief outputs/latest.md
dailynews normalize --in tmp/fetched.json --out tmp/normalized.json --source-id openai-news --source-type rss
dailynews rank --in tmp/normalized.json --out tmp/ranked.json --limit 20 --hot-words config/ranking.json
dailynews collect --sources config/sources.json --out tmp/normalized.json
dailynews prepare --sources config/sources.json --hot-words config/ranking.json --since-hours 24 --fallback-hours 72 --min-sources 2 --max-per-source 3 --limit 7 --out tmp/ranked.json
dailynews summarize --in tmp/ranked.json --out tmp/brief.json --max-items 8
dailynews render-email --in tmp/brief.json --out tmp/brief.html
dailynews send-email --brief tmp/brief.json --html tmp/brief.html --to mejasperj@outlook.com
```

AgentMail helper for inbound newsletter access:

```bash
dailynews agentmail-fetch --limit 25 --metadata-only
dailynews rss-fetch --url https://link.baai.ac.cn/@AI_era.rss --limit 10
dailynews rsshub-fetch rsshub://anthropic/engineering --limit 10
```

### GitHub Action

The workflow runs every day at 08:00 China Standard Time and can also be started manually. Pull requests targeting `main` run the full prepare, summarize, render, validation, and email delivery flow. Secret-backed PR verification only runs for branches inside this repository; fork PRs are skipped.

```text
.github/workflows/daily-brief.yml
```

Required repository Actions secrets:

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

### Skill

Agent instructions that explain when and how to use the CLI for news fetching, briefing, verification, and publishing.

## Email

Email publishing uses Resend.

```text
From: DNA Daily Brief <dna@sharkshark-studio.xyz>
Secret: RESEND_API_KEY
```

Inbound newsletter collection uses AgentMail.

```text
Secrets: AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID
```

Brief summarization will use OpenRouter with DeepSeek V4 Flash.

```text
Secret: OPENROUTER_API_KEY
Base URL: https://openrouter.ai/api/v1
Model: deepseek/deepseek-v4-flash
```

## Process Split

Fetching and summarizing/publishing are separate processes joined by storage.

```text
fetch sources -> store articles -> summarize from storage -> verify brief -> publish
```

This keeps source collection decoupled from LLM usage and delivery. Fetching can fail, retry, or run on its own without sending email. Summarizing can be repeated from stored articles without scraping sources again.

Planned commands:

```bash
dailynews fetch --config config.yaml
dailynews normalize --in tmp/fetched.json --out tmp/normalized.json --source-id openai-news --source-type rss
dailynews rank --in tmp/normalized.json --out tmp/ranked.json --limit 20 --hot-words config/ranking.json
dailynews collect --sources config/sources.json --out tmp/normalized.json
dailynews prepare --sources config/sources.json --hot-words config/ranking.json --since-hours 24 --out tmp/ranked.json
dailynews summarize --topic "ai agents" --since 24h
dailynews push --brief-id latest --to email
dailynews run --config config.yaml
```

`run` should be a convenience command that calls `fetch`, `normalize`, `rank`, `summarize`, and `push` in order.

Normalization turns mixed source outputs into one item schema. Ranking first deduplicates by normalized URL or title, then applies deterministic scoring based on recency, source weight, hot-word relevance, content length, and source URL availability.

Hot words live in [`config/ranking.json`](./config/ranking.json). Increase a term's weight to push matching stories higher.

Runtime sources live in [`config/sources.json`](./config/sources.json). `collect` fetches and normalizes all enabled sources. `prepare` additionally filters by time window, deduplicates, and ranks.

Daily selection prefers the last 24 hours, requires 3 stories from at least 2 sources when possible, caps each source at 3 stories, and returns at most 7. If the 24-hour candidates cannot meet the minimums, selection expands to 72 hours and sends the best available result.

AgentMail source entries can define `exclude_subject_prefixes` to remove signup, verification, welcome, and test messages before normalization and ranking.

## Storage

Use SQLite first. It is enough for local CLI runs, GitHub Actions, and early agent usage.

Initial tables:

```text
sources
articles
runs
briefs
deliveries
```

The database is the boundary between collection and publishing:

- fetchers write raw and normalized articles
- summarizers read stored articles
- publishers send stored briefs

## Source Registry

Fetching sources are tracked in [`docs/sources.md`](./docs/sources.md) as a human-editable registry.

Keep runtime config separate later, likely in YAML. The Markdown table is for planning, review, and simple CRUD by editing rows.

## Initial Structure

```text
src/dailynews/
  core/
  ingest/
  normalize/
  enrich/
  cluster/
  rank/
  synthesize/
  verify/
  publish/
  storage/
  cli.py

docs/
  sources.md

skills/
  dailynews/
    SKILL.md

.github/
  workflows/

tests/
fixtures/
reference/
  v1/
```

## Build Order

1. Core models and pipeline.
2. CLI.
3. GitHub Action.
4. Skill.
5. Optional MCP interface later.
