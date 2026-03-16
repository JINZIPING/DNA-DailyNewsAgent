# DNA-DailyNewsAgent

## Overview
DNA-DailyNewsAgent is a lightweight multi-agent system for fetching, ranking, and summarizing daily news. It is designed around a simple pipeline: the Scout fetches raw articles from enabled news tools, the Analyst removes duplicates and ranks them by popularity, the Synthesizer writes a Markdown brief, and the Editor reviews and saves the final output.

## Quick Start

1. Install python dependencies from `environment.txt`
2. Edit [config.yaml](./config.yaml) (refer to the following Set Up) (PS: turn on "resend" tool if you need email push)
3. Run: `python -m app.main`

## Set Up

### Config File
[config.yaml](./config.yaml) is the default runtime config file. Passing `--config <path>` is optional

### Model API (Mandatory)
The `model_api` block controls the LLM connection:
- `base_url`: optional. Leave `null` for OpenAI directly, or set it for an OpenAI-compatible provider.
- `api_key_env`: environment variable name that stores the API key.
- `model`: model name to use for synthesis.
- `temperature`: sampling temperature.

### Workflow Limits
The `workflow` block controls output size and ranking size:
- `output_dir`: where final Markdown briefs are saved.
- `max_articles`: maximum number of raw articles the Scout keeps.
- `max_filtered_articles`: maximum number of ranked articles the Analyst passes to the Synthesizer.

### Scrape Keywords
The `scraping` block controls fetch input:
- `keywords`: the fetch inputs used by `news_fetch` tools.
- `keywords` are limited to 3 maximum.
- article fields are hardcoded in the app and are not configured in `config.yaml`.

### Tool Config Blocks
Each tool domain has its own config block under `tools`. (can add your own tools)

`tools.news_fetch`
- contains concrete fetch tools such as `hacker_news`
- each concrete tool can define `name`, `enabled`, `base_url`, and optional `api_key_env`

`tools.file_writer`
- contains concrete output writers such as `markdown`
- `api_key_env` is optional

`tools.email_sender`
- contains the `resend` delivery tool
- set `enabled: true` to turn email delivery on
- `api_key_env` points to the Resend API key environment variable
- `default_recipient` is the recipient email address
- `sender_email` is the verified sender used by Resend

## Agent Roles

### Agent 1: The Scout
- Role: uses configured keywords to fetch raw articles from enabled news tools.
- Tools Permitted: `News_Fetch`
- Output: a list of raw articles with URLs, headlines, source metadata, unedited article text, and popularity fields.

### Agent 2: The Analyst
- Role: removes duplicates and ranks articles only by popularity.
- Tools Permitted: none.
- Output: a deduplicated, popularity-ranked list of top articles.

### Agent 3: The Synthesizer
- Role: reads the filtered articles and drafts the daily news brief by combining multiple sources into cohesive summary paragraphs.
- Tools Permitted: none.
- Output: a draft Markdown news brief.

### Agent 4: The Editor
- Role: manages the workflow, verifies the Synthesizer's draft against the original user request, and either approves it or sends revision feedback.
- Tools Permitted: `File_Writer` and `Email_Sender`.
- Output: the approved final brief saved as a Markdown or PDF file, and optionally sent to the user.

## Core Design
- Coordination: centralized orchestrator to assign tasks and pass messages between agents.
- Tooling: `News_Fetch` uses real source methods such as Hacker News.
- Fetch methods: `config.yaml` enables concrete tools under `tools.news_fetch.tools`; the Scout invokes the enabled fetch tools directly.
- Permissions: tool access is declared directly in each agent module instead of a shared registry layer.
- Tool structure: `news_fetch`, `file_writer`, and `email_sender` each live in their own folder so additional methods can be added without flattening the tools directory.
- Tool config: each tool domain contains multiple concrete tools, and each concrete tool uses the same base config fields: `name`, `enabled`, `base_url`, and `api_key_env`.
- State: shared task state for the workflow, plus per-agent memory for intermediate results.
- Runtime config: root-level `config.yaml` controls model settings, scrape keywords, workflow limits, and per-tool configuration.
