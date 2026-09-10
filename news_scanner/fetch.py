"""Pull and normalize items from the configured RSS feeds."""

import re
import sys
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"

_TAG_RE = re.compile(r"<[^>]+>")
_SUMMARY_LIMIT = 600


def _clean_summary(html):
    """Strip markup and cap length - some feeds (e.g. NOS) put the full
    article body in <summary>, which is unnecessary input for the relevance
    call downstream."""
    text = _TAG_RE.sub(" ", html or "")
    return " ".join(text.split())[:_SUMMARY_LIMIT]


def load_sources(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _entry_published_at(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc).isoformat()


def _is_skipped(entry, filter_rule):
    """Mixed-source paywall filtering (see config/sources.yaml, e.g. AD).

    Sources don't agree on how they mark paid content - some use a real RSS
    <category>, AD uses a custom `dpp_paid` element - so this checks whatever
    field/value pair that source's config says to skip.
    """
    if not filter_rule:
        return False
    field = filter_rule.get("skip_field")
    value = filter_rule.get("skip_value")
    if not field:
        return False
    return str(entry.get(field, "")).lower() == str(value).lower()


def fetch_feed(source_name, language, feed_url, filter_rule=None):
    parsed = feedparser.parse(feed_url)
    items = []
    for entry in parsed.entries:
        if _is_skipped(entry, filter_rule):
            continue
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        if not title or not url:
            continue
        items.append({
            "title": title,
            "url": url,
            "source": source_name,
            "language": language,
            "published_at": _entry_published_at(entry),
            "raw_summary": _clean_summary(entry.get("summary", "")),
        })
    return items


def fetch_all(sources=None):
    """Fetch and normalize every configured feed. See config/sources.yaml."""
    sources = sources or load_sources()
    items = []
    for source in sources:
        filter_rule = source.get("filter")
        for feed in source["feeds"]:
            items.extend(fetch_feed(
                source["name"], source["language"], feed["url"], filter_rule
            ))
    return items


def check_feeds(sources=None):
    """Verify every configured feed resolves and returns at least one entry.

    Feed paths move without notice (see config/sources.yaml's header) — run
    this by hand before relying on the list, e.g. `python -m news_scanner.fetch --check-feeds`.
    """
    sources = sources or load_sources()
    ok = True
    for source in sources:
        for feed in source["feeds"]:
            parsed = feedparser.parse(feed["url"])
            label = feed.get("label")
            name = f"{source['name']} ({label})" if label else source["name"]
            if parsed.bozo and not parsed.entries:
                ok = False
                print(f"FAIL  {name}: {feed['url']} - {parsed.bozo_exception}")
            elif not parsed.entries:
                ok = False
                print(f"EMPTY {name}: {feed['url']} - resolved but no entries")
            else:
                print(f"OK    {name}: {feed['url']} - {len(parsed.entries)} entries")
    return ok


if __name__ == "__main__":
    if "--check-feeds" in sys.argv:
        sys.exit(0 if check_feeds() else 1)
    for item in fetch_all():
        print(item)
