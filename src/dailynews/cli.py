from __future__ import annotations

import argparse
import json
from pathlib import Path

from dailynews.core.models import NormalizedItem
from dailynews.core.pipeline import prepare_items
from dailynews.ingest.agentmail import fetch_messages, message_summaries
from dailynews.ingest.collector import collect_sources, load_sources
from dailynews.ingest.rss import AI_ERA_RSS_URL, fetch_rss_items
from dailynews.ingest.rsshub import (
    DEFAULT_RSSHUB_IMAGE,
    DEFAULT_RSSHUB_PORT,
    rsshub_route_url,
    temporary_rsshub,
)
from dailynews.llm.openrouter import OpenRouterClient
from dailynews.normalize.items import normalize_records
from dailynews.publish.email import EmailMessage, send_email
from dailynews.publish.email_renderer import email_subject, render_email
from dailynews.rank.scoring import HotWord, rank_items
from dailynews.summarize.brief import DailyBrief, summarize_ranked_items


def main() -> None:
    try:
        _main()
    except RuntimeError as exc:
        raise SystemExit(f"Error: {exc}") from exc


def _main() -> None:
    parser = argparse.ArgumentParser(prog="dailynews")
    subparsers = parser.add_subparsers(dest="command", required=True)

    agentmail_fetch = subparsers.add_parser("agentmail-fetch")
    agentmail_fetch.add_argument("--limit", type=int, default=25)
    agentmail_fetch.add_argument("--after", help="ISO timestamp lower bound.")
    agentmail_fetch.add_argument(
        "--metadata-only",
        action="store_true",
        help="Print message metadata without raw message bodies.",
    )
    agentmail_fetch.add_argument("--out", help="Write JSON output to this file.")
    rss_fetch = subparsers.add_parser("rss-fetch")
    rss_fetch.add_argument("--url", default=AI_ERA_RSS_URL)
    rss_fetch.add_argument("--limit", type=int, default=25)
    rss_fetch.add_argument("--timeout", type=int, default=20)
    rss_fetch.add_argument("--out", help="Write JSON output to this file.")
    rsshub_fetch = subparsers.add_parser("rsshub-fetch")
    rsshub_fetch.add_argument("route", help="RSSHub route, for example rsshub://anthropic/engineering.")
    rsshub_fetch.add_argument("--limit", type=int, default=25)
    rsshub_fetch.add_argument("--timeout", type=int, default=60)
    rsshub_fetch.add_argument("--port", type=int, default=DEFAULT_RSSHUB_PORT)
    rsshub_fetch.add_argument("--image", default=DEFAULT_RSSHUB_IMAGE)
    rsshub_fetch.add_argument("--out", help="Write JSON output to this file.")
    normalize = subparsers.add_parser("normalize")
    normalize.add_argument("--in", dest="input_path", required=True)
    normalize.add_argument("--out", dest="output_path", required=True)
    normalize.add_argument("--source-id", required=True)
    normalize.add_argument("--source-type", required=True)
    rank = subparsers.add_parser("rank")
    rank.add_argument("--in", dest="input_path", required=True)
    rank.add_argument("--out", dest="output_path", required=True)
    rank.add_argument("--limit", type=int, default=25)
    rank.add_argument("--keywords", default="", help="Comma-separated ranking keywords.")
    rank.add_argument("--hot-words", help="Path to ranking JSON with weighted hot words.")
    collect = subparsers.add_parser("collect")
    collect.add_argument("--sources", default="config/sources.json")
    collect.add_argument("--out", required=True)
    collect.add_argument("--rsshub-port", type=int, default=DEFAULT_RSSHUB_PORT)
    collect.add_argument("--rsshub-image", default=DEFAULT_RSSHUB_IMAGE)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--sources", default="config/sources.json")
    prepare.add_argument("--hot-words", default="config/ranking.json")
    prepare.add_argument("--out", required=True)
    prepare.add_argument("--since-hours", type=int, default=24)
    prepare.add_argument("--fallback-hours", type=int, default=72)
    prepare.add_argument("--min-items", type=int, default=3)
    prepare.add_argument("--min-sources", type=int, default=2)
    prepare.add_argument("--limit", type=int, default=7)
    prepare.add_argument("--max-per-source", type=int, default=3)
    prepare.add_argument("--rsshub-port", type=int, default=DEFAULT_RSSHUB_PORT)
    prepare.add_argument("--rsshub-image", default=DEFAULT_RSSHUB_IMAGE)
    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--in", dest="input_path", required=True)
    summarize.add_argument("--out", dest="output_path", required=True)
    summarize.add_argument("--max-items", type=int, default=8)
    render = subparsers.add_parser("render-email")
    render.add_argument("--in", dest="input_path", required=True)
    render.add_argument("--out", dest="output_path", required=True)
    send = subparsers.add_parser("send-email")
    send.add_argument("--brief", required=True)
    send.add_argument("--html", required=True)
    send.add_argument("--to", required=True)

    args = parser.parse_args()

    if args.command == "agentmail-fetch":
        response = fetch_messages(limit=args.limit, after=args.after)
        output = message_summaries(response) if args.metadata_only else response
        _emit_json(output, output_path=args.out)
        return

    if args.command == "rss-fetch":
        items = fetch_rss_items(args.url, limit=args.limit, timeout=args.timeout)
        _emit_json([item.to_dict() for item in items], output_path=args.out)
        return

    if args.command == "rsshub-fetch":
        with temporary_rsshub(image=args.image, port=args.port) as base_url:
            url = rsshub_route_url(args.route, base_url=base_url)
            items = fetch_rss_items(url, limit=args.limit, timeout=args.timeout)
        _emit_json([item.to_dict() for item in items], output_path=args.out)
        return

    if args.command == "normalize":
        records = _read_json(args.input_path)
        items = normalize_records(records, source_id=args.source_id, source_type=args.source_type)
        _write_json(args.output_path, [item.to_dict() for item in items])
        return

    if args.command == "rank":
        records = _read_json(args.input_path)
        raw_items = records if isinstance(records, list) else []
        items = [NormalizedItem.from_dict(dict(item)) for item in raw_items if isinstance(item, dict)]
        hot_words = _load_hot_words(args.hot_words)
        cli_keywords = [keyword.strip() for keyword in args.keywords.split(",") if keyword.strip()]
        hot_words.extend(HotWord(keyword, 6) for keyword in cli_keywords)
        ranked = rank_items(items, limit=args.limit, hot_words=hot_words or None)
        _write_json(args.output_path, [item.to_dict() for item in ranked])
        return

    if args.command == "collect":
        sources = load_sources(args.sources)
        items = collect_sources(
            sources,
            rsshub_image=args.rsshub_image,
            rsshub_port=args.rsshub_port,
        )
        _write_json(args.out, [item.to_dict() for item in items])
        return

    if args.command == "prepare":
        sources = load_sources(args.sources)
        items = collect_sources(
            sources,
            rsshub_image=args.rsshub_image,
            rsshub_port=args.rsshub_port,
        )
        hot_words = _load_hot_words(args.hot_words)
        ranked = prepare_items(
            items,
            since_hours=args.since_hours,
            fallback_hours=args.fallback_hours,
            min_items=args.min_items,
            min_sources=args.min_sources,
            limit=args.limit,
            max_per_source=args.max_per_source,
            hot_words=hot_words or None,
        )
        _write_json(args.out, [item.to_dict() for item in ranked])
        return

    if args.command == "summarize":
        records = _read_json(args.input_path)
        raw_items = records if isinstance(records, list) else []
        brief = summarize_ranked_items(
            [dict(item) for item in raw_items if isinstance(item, dict)],
            OpenRouterClient(),
            max_items=args.max_items,
        )
        _write_json(args.output_path, brief.to_dict())
        return

    if args.command == "render-email":
        payload = _read_json(args.input_path)
        if not isinstance(payload, dict):
            raise RuntimeError("Brief input must be a JSON object.")
        html = render_email(DailyBrief.from_dict(payload))
        _write_text(args.output_path, html)
        return

    if args.command == "send-email":
        payload = _read_json(args.brief)
        if not isinstance(payload, dict):
            raise RuntimeError("Brief input must be a JSON object.")
        brief = DailyBrief.from_dict(payload)
        html = Path(args.html).read_text(encoding="utf-8")
        response = send_email(
            EmailMessage(
                to=args.to,
                subject=email_subject(brief),
                html=html,
            )
        )
        print(json.dumps(response, indent=2))


def _emit_json(data: object, *, output_path: str | None) -> None:
    if output_path:
        _write_json(output_path, data)
        return
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _read_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, data: object) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: str, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _load_hot_words(path: str | None) -> list[HotWord]:
    if not path:
        return []
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise RuntimeError("Hot words config must be a JSON object.")
    hot_words = payload.get("hot_words", [])
    if not isinstance(hot_words, list):
        raise RuntimeError("Hot words config field 'hot_words' must be a list.")
    loaded: list[HotWord] = []
    for item in hot_words:
        if isinstance(item, str):
            loaded.append(HotWord(item, 6))
            continue
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        if term:
            loaded.append(HotWord(term, float(item.get("weight", 6))))
    return loaded


if __name__ == "__main__":
    main()
