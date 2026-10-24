"""Tracks which articles have already been handled, so 07:00/19:00 never
repeat a story. See CLAUDE.md's content rules.

Two tables: `sent` for articles that went out in a digest, and `skipped` for
articles the pipeline paid to judge but left out because only one outlet
covered them. Both are filtered out before the (costly) Claude stages -
without `skipped`, every left-out article would be re-judged by Haiku on
each run until it fell out of its feed."""

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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS skipped ("
        "url TEXT PRIMARY KEY, "
        "title TEXT, "
        "source TEXT, "
        "skipped_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    return conn


def dedupe(items, path=DB_PATH):
    """Drop anything already sent in an earlier digest or already skipped as
    single-outlet, and any duplicate URL within this run itself."""
    conn = _connect(path)
    try:
        seen_this_run = set()
        fresh = []
        for item in items:
            url = item["url"]
            if url in seen_this_run:
                continue
            already_handled = conn.execute(
                "SELECT 1 FROM sent WHERE url = ? "
                "UNION SELECT 1 FROM skipped WHERE url = ?",
                (url, url),
            ).fetchone()
            if already_handled:
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


def mark_skipped(items, path=DB_PATH):
    """Record items that were judged but left out of the digest because only
    one outlet covered them, so later runs don't pay to judge them again. Same
    rule as mark_sent: only after a real (non-dry-run) send."""
    conn = _connect(path)
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO skipped (url, title, source) VALUES (?, ?, ?)",
            [(item["url"], item["title"], item["source"]) for item in items],
        )
        conn.commit()
    finally:
        conn.close()
