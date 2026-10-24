"""Tracks which articles have already been handled, so 07:00/19:00 never
repeat a story. See CLAUDE.md's content rules.

Three tables:
- `sent`: articles that went out in a digest.
- `skipped`: articles the pipeline paid to judge and won't use again - Haiku
  rejected them as off-topic, or they stayed single-outlet through every
  hold-over run (see below).
- `held`: single-outlet articles waiting for a second outlet to cover the same
  story. Stored whole, including Haiku's summary, so they can rejoin the next
  runs' clustering without being judged again.

All three are filtered out of fresh feed items before the (costly) Claude
stages. Without them, every article that didn't make a digest would be
re-judged by Haiku on each run until it fell out of its feed."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "state" / "sent.sqlite3"

# How many later runs a single-outlet article is carried into before giving
# up on a second outlet. At two runs a day, 2 means roughly 24 hours. Must be
# at least 1.
HOLD_RUNS = 2


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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS held ("
        "url TEXT PRIMARY KEY, "
        "title TEXT, "
        "source TEXT, "
        "item TEXT, "
        "held_over INTEGER DEFAULT 0, "
        "held_at TEXT DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    return conn


def dedupe(items, path=DB_PATH):
    """Drop anything already sent, skipped, or currently held (held items
    come back through load_held, not through the feed), and any duplicate URL
    within this run itself."""
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
                "UNION SELECT 1 FROM skipped WHERE url = ? "
                "UNION SELECT 1 FROM held WHERE url = ?",
                (url, url, url),
            ).fetchone()
            if already_handled:
                continue
            seen_this_run.add(url)
            fresh.append(item)
        return fresh
    finally:
        conn.close()


def mark_sent(items, path=DB_PATH):
    """Record items as sent - only call this after a real (non-dry-run) send.
    An item that was being held for a second outlet is released from `held`."""
    conn = _connect(path)
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO sent (url, title, source) VALUES (?, ?, ?)",
            [(item["url"], item["title"], item["source"]) for item in items],
        )
        conn.executemany(
            "DELETE FROM held WHERE url = ?", [(item["url"],) for item in items]
        )
        conn.commit()
    finally:
        conn.close()


def mark_skipped(items, path=DB_PATH):
    """Record items that were judged and won't be used, so later runs don't
    pay to judge them again. Same rule as mark_sent: only after a real
    (non-dry-run) run."""
    conn = _connect(path)
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO skipped (url, title, source) VALUES (?, ?, ?)",
            [(item["url"], item["title"], item["source"]) for item in items],
        )
        conn.commit()
    finally:
        conn.close()


def load_held(path=DB_PATH):
    """Single-outlet items still waiting for a second outlet, oldest first -
    the full item dicts, as they were when first held."""
    conn = _connect(path)
    try:
        rows = conn.execute("SELECT item FROM held ORDER BY held_at, rowid").fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


def hold(items, path=DB_PATH):
    """Record items that were just clustered without finding a second outlet.
    A new one is held for the next runs. One that was already held has now
    been through another run with no second outlet turning up; once it has
    been carried through HOLD_RUNS runs it's moved to `skipped` for good."""
    conn = _connect(path)
    try:
        for item in items:
            url = item["url"]
            row = conn.execute(
                "SELECT held_over FROM held WHERE url = ?", (url,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO held (url, title, source, item, held_over) "
                    "VALUES (?, ?, ?, ?, 0)",
                    (url, item["title"], item["source"],
                     json.dumps(item, ensure_ascii=False)),
                )
            elif row[0] + 1 >= HOLD_RUNS:
                conn.execute(
                    "INSERT OR IGNORE INTO skipped (url, title, source) "
                    "VALUES (?, ?, ?)",
                    (url, item["title"], item["source"]),
                )
                conn.execute("DELETE FROM held WHERE url = ?", (url,))
            else:
                conn.execute(
                    "UPDATE held SET held_over = ? WHERE url = ?", (row[0] + 1, url)
                )
        conn.commit()
    finally:
        conn.close()
