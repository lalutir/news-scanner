# news-scanner

A twice-daily politics/geopolitics/conflict news digest — fetched from a curated set of English- and Dutch-language sources, emailed at 07:00 and 19:00, and shown on `news.lalutir.com` behind a newsletter dropdown. Backend and site live in this one repo.

> **A note on the template.** This repo started from [lalutir/template](https://github.com/lalutir/template) — the **Seaglass** design system for lalutir.com pages. Only `site/` actually uses it; the fetch/filter/send pipeline has no UI and doesn't touch Seaglass at all. See `CLAUDE.md` for exactly where that line is drawn, and for the real Caddy/deploy pattern this project follows (pulled from the live `lalutir.com` and `p2000-reader` repos).

## What it does

- Pulls new articles from a fixed list of RSS feeds — see `CLAUDE.md` for the starting list
- Keeps only what's on-topic: politics, geopolitics, war and conflict, national and international
- Skips paywalled sources, and skips the paywalled portion of mixed sources
- Emails one digest at **07:00** and one at **19:00**, Europe/Amsterdam, via a systemd timer
- Publishes the same digest to `news.lalutir.com`, where a dropdown selects between registered newsletters (one for now)
- Never repeats a story already sent in an earlier digest

## Prerequisites

- The mail build from `mailserver.pdf` already done — Mailcow, Cloudflare DNS, Mailgun verified as the sending domain (`mg.lalutir.com`).
- A sending address and a scoped Mailgun API key for this project specifically.
- SSH access to the droplet as the `lalutir` user, same as every other project there.
- An `A` record for `news` in Cloudflare, pointing at the droplet.
- Python 3.11+.
- An Anthropic API key — filtering and the daily briefing both call Claude Haiku (see the tradeoffs in `CLAUDE.md`), so this one isn't optional.

## Configuration

Backend config lives in environment variables (`.env`, not committed) — the site itself needs none, it just reads JSON files sitting next to it:

| Variable | Purpose |
|---|---|
| `MAILGUN_API_KEY` | Scoped Mailgun API key used to send the digest |
| `MAILGUN_DOMAIN` | `mg.lalutir.com` |
| `DIGEST_FROM_EMAIL` | The sending address, e.g. `noreply@lalutir.com` |
| `DIGEST_RECIPIENTS` | Comma-separated recipient list |
| `ANTHROPIC_API_KEY` | Used by every run — Claude Haiku makes the relevance call, writes summaries, and drafts the daily briefing |

## Getting started

1. Copy `.env.example` to `.env` and fill it in.
2. `python -m venv venv && venv/bin/pip install -r requirements.txt` (Windows: `venv\Scripts\pip install -r requirements.txt`).
3. Do one dry run against the configured feeds without sending — `python -m news_scanner.run --dry-run` — to sanity-check filtering before anything reaches an inbox or the site.
4. Send one real test digest to yourself — `python -m news_scanner.run` — and confirm `site/data/politics-geopolitics/latest.json` gets written correctly.
5. SSH into the droplet as `lalutir` and run `scripts/deploy.sh` from `/home/lalutir/news-scanner` — it installs the systemd timer *and* the Caddy snippet in one pass. See `CLAUDE.md` → Infrastructure for exactly what it does.
6. Add a card for `news.lalutir.com` to the separate `lalutir.com` repo's homepage, and deploy that repo once — a one-time step outside this project.

## What's in here

```
.
├── CLAUDE.md
├── README.md
├── .env.example
├── requirements.txt
├── config/
│   ├── sources.yaml          # source list: name, feed URL, language, paywall notes
│   └── keywords.yaml         # EN/NL pre-filter terms, checked before the Claude call
├── news_scanner/
│   ├── settings.py             # loads .env once for every stage below
│   ├── fetch.py               # pull + parse the configured feeds
│   ├── filter.py              # keyword pre-filter, then Claude Haiku
│   ├── dedupe.py              # tracks what's already been sent
│   ├── digest.py              # compiles the HTML/plaintext email + daily briefing
│   ├── send.py                # Mailgun API call
│   ├── publish.py             # writes site/data/<id>/latest.json
│   └── run.py                 # one full fetch → filter → dedupe → send → publish cycle
├── site/                       # news.lalutir.com — Seaglass, zero build step
│   ├── index.html               # dropdown + rendered entries
│   ├── 404.html
│   ├── data/
│   │   ├── newsletters.json      # registry the dropdown reads
│   │   └── politics-geopolitics/
│   │       └── latest.json        # written by publish.py, gitignored
│   └── assets/
│       ├── css/
│       │   ├── tokens.css          # Seaglass — copied in unchanged
│       │   └── site.css
│       └── js/
│           └── site.js             # dropdown + fetch/render logic
├── state/
│   └── sent.sqlite3             # local dedup store, gitignored
├── systemd/
│   ├── news-scanner.service
│   └── news-scanner.timer
├── caddy/
│   └── news.caddy               # this repo's Caddy snippet
└── scripts/
    └── deploy.sh                 # installs the timer and the Caddy snippet
```

## Sources, rules, and architecture

The full source list, the paywall/language rules, the Seaglass rules for `site/`, the exact Caddy/systemd/deploy pattern, and the known tradeoffs all live in `CLAUDE.md` — that's the canonical reference, kept current so a fresh Claude Code session doesn't have to rediscover any of it.