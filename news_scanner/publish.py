"""Writes site/data/<newsletter_id>/latest.json - the JSON the site reads.
Schema documented in CLAUDE.md's "The newsletter registry" section."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NEWSLETTER_ID = "politics-geopolitics"
TZ = ZoneInfo("Europe/Amsterdam")
DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "site" / "data" / NEWSLETTER_ID / "latest.json"
)


def current_run(now=None):
    """'am' before noon local time, 'pm' otherwise - matches the 07:00/19:00
    schedule (see systemd/news-scanner.timer)."""
    now = now or datetime.now(TZ)
    return "am" if now.hour < 12 else "pm"


def build_payload(items, briefing, run=None, generated_at=None):
    generated_at = generated_at or datetime.now(TZ)
    run = run or current_run(generated_at)
    return {
        "newsletter_id": NEWSLETTER_ID,
        "generated_at": generated_at.isoformat(),
        "run": run,
        "briefing": briefing,
        "entries": [
            {
                "title": item["title"],
                "source": item["source"],
                "url": item["url"],
                "language": item["language"],
                "published_at": item["published_at"],
                "summary": item["summary"],
            }
            for item in items
        ],
    }


def publish(items, briefing, path=DATA_PATH, run=None, generated_at=None):
    payload = build_payload(items, briefing, run=run, generated_at=generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload
