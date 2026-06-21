# Source Registry

Human-editable registry for planned fetching sources.

This table is for review and lightweight CRUD by editing rows. Runtime config should stay separate once source loading is implemented.

| ID | Type | Name | URL | Enabled | Topics | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| agentmail-inbox | email | AgentMail Inbox | env:AGENTMAIL_INBOX_ID | yes | newsletters | Inbound newsletter collector; uses `AGENTMAIL_API_KEY` |
| ai-era-baai | rss | 新智元 / AI Era | https://link.baai.ac.cn/@AI_era.rss | yes | ai, cn-ai | Mastodon RSS feed; posts link to BAAI Hub articles |
| anthropic-research-rsshub | rsshub | Anthropic Research | rsshub://anthropic/research | yes | ai, anthropic, research | Requires one-time/local RSSHub |
| github-trending-daily | rsshub | GitHub Trending Daily | rsshub://github/trending/daily/any | yes | development, trending | Requires one-time/local RSSHub and `RSSHUB_GITHUB_ACCESS_TOKEN` |
| openai-news | rss | OpenAI News | https://openai.com/news/rss.xml | yes | ai, openai, research | Official OpenAI RSS feed |
| latent-space | rss | Latent Space | https://www.latent.space/feed | yes | ai, agents, newsletter | v1 source; AI engineering/newsletter feed |
| hugging-face-blog | rss | Hugging Face Blog | https://huggingface.co/blog/feed.xml | yes | ai, ml, research | v1 source; official Hugging Face blog |
| sebastian-raschka | rss | Sebastian Raschka | https://magazine.sebastianraschka.com/feed | yes | ai, ml, research | Technical ML/AI articles |
| hacker-news-topstories | api | Hacker News Top Stories | https://hacker-news.firebaseio.com/v0 | yes | tech, ai, programming | v1 source; API adapter not ported yet |
| last-week-in-ai | rss | Last Week in AI | https://lastweekin.ai/feed | yes | ai, newsletter | AI news podcast/newsletter feed |

## CRUD Notes

- Add a source by adding a row.
- Disable a source by setting `Enabled` to `no`.
- Update source metadata directly in the table.
- Remove a source by deleting its row.
