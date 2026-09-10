"""Tracks which articles have already been sent, so 07:00/19:00 never
repeat a story. See CLAUDE.md's content rules."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "state" / "sent.sqlite3"


def _connect(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sent ("
        "url TEXT PRIMARY KEY, "
        "title TEXT, "
        "source TEXT, "
        "sent_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    return conn


def dedupe(items, path=DB_PATH):
    """Drop anything already sent in an earlier digest, and any duplicate
    URL within this run itself."""
    conn = _connect(path)
    try:
        seen_this_run = set()
        fresh = []
        for item in items:
            url = item["url"]
            if url in seen_this_run:
                continue
            already_sent = conn.execute(
                "SELECT 1 FROM sent WHERE url = ?", (url,)
            ).fetchone()
            if already_sent:
                continue
            seen_this_run.add(url)
            fresh.append(item)
        return fresh
    finally:
        conn.close()


def mark_sent(items, path=DB_PATH):
    """Record items as sent - only call this after a real (non-dry-run) send."""
    conn = _connect(path)
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO sent (url, title, source) VALUES (?, ?, ?)",
            [(item["url"], item["title"], item["source"]) for item in items],
        )
        conn.commit()
    finally:
        conn.close()
