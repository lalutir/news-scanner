# news-scanner

A twice-daily politics/geopolitics/conflict news digest: a backend pipeline that fetches, filters, and emails it, plus the `news.lalutir.com` site that displays it. Both live in this one repo. Read this whole file before writing any code.

**On the template lineage.** This repo started from `lalutir/template`, the **Seaglass** design system for lalutir.com's front-end pages. Only part of this repo is a front-end: `site/` is the actual `news.lalutir.com` page and *does* use Seaglass in full (see "Design system" below); everything outside `site/` — the fetch/filter/send pipeline — has no UI and doesn't reference Seaglass at all. Keep that boundary clean: no glass tokens or `.glass-focus` outside `site/`, and no API keys, RSS parsing, or Mailgun calls inside it.

Worth naming explicitly: putting the site in this repo, rather than its own, is a deliberate choice against the droplet's usual pattern (see `lalutir.com`'s own README, "Adding a new subdomain" — normally one repo per subdomain, e.g. `p2000-reader`, `world-cup-predictor`). `site/` is effectively its own copy of `lalutir/template`, nested here instead of split out, because it has nothing to show without this repo's own output. If the site ever needs to display a newsletter this repo doesn't produce, that's the moment to revisit the split — see "Adding a newsletter" below.

## Pipeline map

<!-- Fill in as each stage gets built. Keep this current — it's the fastest way
     for a fresh Claude Code session to understand the project. -->

| Stage | Purpose | Status |
|---|---|---|
| Fetch | Pull new items from the configured RSS feeds | Done (`news_scanner/fetch.py`) |
| Dedupe | Drop anything already sent, *before* filtering - most of a feed's entries are still there from the previous run, and Haiku is the costly step | Done (`news_scanner/dedupe.py`) |
| Filter | Keep politics/geopolitics/conflict, drop paywalled items | Done (`news_scanner/filter.py` — keyword pre-filter, then Claude Haiku, run only on unseen items) |
| Digest | Compile the HTML + plaintext email | Done (`news_scanner/digest.py` — includes a synthesized daily-briefing paragraph) |
| Send | Deliver via the Mailgun API | Done (`news_scanner/send.py`) |
| Publish | Write `site/data/politics-geopolitics/latest.json` for the site to read | Done (`news_scanner/publish.py`) |
| Schedule | Trigger at 07:00 and 19:00 Europe/Amsterdam | Done (`systemd/news-scanner.{service,timer}` written; not yet installed on the droplet) |

## Site map (`site/`)

<!-- Same idea as the template: fill in as pages get built. -->

| Path | Purpose | Status |
|---|---|---|
| `/` | Home — newsletter dropdown + the selected newsletter's latest entries | Done |
| `/404.html` | Custom not-found page | Done |

## What's placeholder

<!-- Same idea as the template: list anything that's a stand-in so nobody mistakes
     a draft for done. Delete a line once the real thing replaces it. -->

- The source table below is a starting point gathered from public RSS directories in September 2026 — feeds move; all resolved as of 2026-09-10 (`python -m news_scanner.fetch --check-feeds` re-verifies on demand), but re-check before assuming that stays true indefinitely.
- `DIGEST_RECIPIENTS` in the real `.env` has a single test address (the maintainer's own) for dry-run/first-send testing — no real subscriber list yet.
- `MAILGUN_API_KEY` and `ANTHROPIC_API_KEY` are still blank in `.env` — both need filling in before a real (non-dry-run) send works.
- `site/assets/og-image.png`, `site/assets/favicon.svg` — same placeholder status as lalutir.com's own pages; the site works without them, add when convenient.

## Content rules

<!-- What's allowed into a digest — separate from the Seaglass rules below, which
     govern how site/ looks rather than what the digest contains. -->

Non-negotiable:
- English and Dutch sources only.
- Politics, geopolitics, war and conflict — national and international. Not general news, sport, or entertainment, unless a story is genuinely about politics or conflict within one of those beats.
- No source that sits behind a hard paywall. For a mixed source, pull only the free tier and skip anything tagged premium/subscriber-only.
- Every item links to the original article — this digest is a pointer, not a republication. A headline and a one- or two-sentence description is enough; don't copy full article text into the email body or onto the site.
- No story appears twice in one digest, and nothing already sent in an earlier digest gets sent again.

Anti-patterns: adding a source just because it has an RSS feed, without checking its paywall model first — several major outlets added metered paywalls in 2024 and are easy to assume are still fully open (see CNN and Reuters below); letting one high-volume source dominate a digest.

## Sources (starting list)

<!-- Verified September 2026. Re-check before wiring in — RSS paths change without notice. -->

| Source | Language | Feed(s) | Paywall |
|---|---|---|---|
| NOS | NL | `feeds.nos.nl/nosnieuwsbuitenland` (foreign), `feeds.nos.nl/nosnieuwspolitiek` (politics) | None |
| VRT NWS | NL | `vrt.be/vrtnws/nl.rss.headlines.xml` | None |
| BBC News | EN | `feeds.bbci.co.uk/news/world/rss.xml`, `.../news/world/europe/rss.xml`, `.../news/world/middle_east/rss.xml`, `.../news/politics/rss.xml?edition=uk` (UK politics specifically) | None |
| Al Jazeera English | EN | `aljazeera.com/xml/rss/all.xml` | None |
| DW (Deutsche Welle) | EN | `rss.dw.com/rdf/rss-en-top` | None |
| The Guardian | EN | `theguardian.com/world/rss`, `.../politics/rss`, `.../world/europe-news/rss` | None — no metered wall by editorial policy |
| Euronews | EN | `euronews.com/rss` | None |
| France 24 | EN | `france24.com/en/rss` | None |
| NL Times | EN (about NL) | `nltimes.nl/rssfeed2` | None |
| DutchNews.nl | EN (about NL) | `dutchnews.nl/feed` | None |
| Algemeen Dagblad (AD) | NL | `ad.nl/home/rss.xml` | Mixed — everyday news is free, "Premium" (yellow-tagged) pieces are metered. Filter those out rather than dropping AD entirely. |
| CNN | EN | — | Added a metered paywall in the US in Oct 2024, extended further since (an "All Access" tier followed a year later). Doesn't cleanly meet the rule above — a judgment call, not a clean include. |
| Reuters | EN | — | Metered paywall since Oct 2024; public RSS was also discontinued in 2020. Excluded. |

Also considered and excluded: NRC, de Volkskrant, Trouw — all subscriber-first Dutch papers with no meaningful free tier.

## Design system — Seaglass (`site/` only)

<!-- Copied from lalutir/template / lalutir.com's own CLAUDE.md, unchanged. Applies
     ONLY inside site/ — nothing in the backend pipeline should ever reference
     these tokens or classes. -->

Tumbled sea glass, not "frosted UI glass." Frosted, tinted, never perfectly clear, edges softened rather than sharp — glass with a history, not a filter effect. Deliberately **not**: cream-plus-serif-plus-terracotta, near-black-plus-one-acid-accent, or plain white/grey iOS-style glass.

Non-negotiable rules:
- Reference tokens only (`site/assets/css/tokens.css`). Never hardcode a hex, `rgba()`, or px spacing in a page or in `site.css`.
- Glass is always tinted (`--glass-tint-*`) — never plain white/grey translucent.
- `--cobalt-rare` appears **once per screen, max** — likely the dropdown itself, given how little else is on this page.
- Respect `prefers-reduced-motion` *and* `prefers-reduced-transparency` — both already handled in `tokens.css`.
- Display type (Fraunces) stays forced to its low-`opsz` cut on headings, same as every other Seaglass page.
- Signature motion (`.glass-focus`) is for showcase moments only — the digest list itself is for scanning, closer to how lalutir.com's own `/resume/` is treated than a hero section. Don't apply it to individual entries.

Anti-patterns: numbered 01/02/03 markers unless content is a genuine sequence; more than one hero-style gradient per page; cards covering every inch of the `--sand` background.

## Infrastructure — don't relearn this by trial and error

<!-- Pulled from the live lalutir.com and p2000-reader repos, since this project
     shares their droplet and conventions. -->

- Everything runs on the same droplet as the rest of lalutir.com, under the `lalutir` user, at `/home/lalutir/news-scanner/` — same convention as `lalutir.com` and `p2000-reader`.
- Mail is already built per `mailserver.pdf`: Mailcow + Cloudflare DNS + Mailgun as the outbound relay (DigitalOcean blocks port 25 on new droplets), sending domain `mg.lalutir.com`, mail hostname `mail.lalutir.com`.
- The backend sends via Mailgun's HTTP API directly, with its own scoped API key — not by routing through Mailcow's SMTP submission port.
- **The Mailgun account is EU-region.** Always post to `api.eu.mailgun.net`, never `api.mailgun.net` (US) — the US endpoint rejects an EU key with a bare `401 Forbidden` that gives no hint it's a region mismatch rather than a bad key. Learned this the hard way on the first real droplet run.
- Sending address: `noreply@lalutir.com`, either works once the DNS checks out. 
- **The twice-daily run is a systemd timer, not cron** — matches how `p2000.lalutir.com` already uses systemd for its own background process on this droplet, and gives cleaner logs (`journalctl -u news-scanner`) than crontab would:

  ```ini
  # systemd/news-scanner.service
  [Unit]
  Description=news-scanner digest run

  [Service]
  Type=oneshot
  User=lalutir
  WorkingDirectory=/home/lalutir/news-scanner
  EnvironmentFile=/home/lalutir/news-scanner/.env
  ExecStart=/home/lalutir/news-scanner/venv/bin/python -m news_scanner.run
  ```

  ```ini
  # systemd/news-scanner.timer
  [Unit]
  Description=Run news-scanner at 07:00 and 19:00

  [Timer]
  OnCalendar=*-*-* 07:00:00
  OnCalendar=*-*-* 19:00:00
  Timezone=Europe/Amsterdam
  Persistent=true

  [Install]
  WantedBy=timers.target
  ```

  The `Timezone=` line is what actually guarantees Europe/Amsterdam — set it on the timer itself rather than relying on a `TZ` environment variable or the droplet's default (which is UTC unless changed).

- **The site is served the same way `world-cup-simulation.lalutir.com` is: plain static, no backend process of its own.** Because `publish` writes straight into this same repo's `site/data/`, Caddy never needs to reach into another project's directory — it's one `file_server` block:

  ```caddyfile
  # caddy/news.caddy
  news.lalutir.com {
      root * /home/lalutir/news-scanner/site
      file_server
  }
  ```

- **Deploy** (`scripts/deploy.sh`) does everything in one pass, the same shape as `p2000-reader`'s own script — SSHes in, pulls, installs backend deps, re-copies the systemd units and the Caddy snippet, reloads both:

  ```bash
  cd /home/lalutir/news-scanner
  git pull
  python3 -m venv venv --upgrade-deps && source venv/bin/activate
  pip install -r requirements.txt && deactivate
  sudo cp systemd/news-scanner.service systemd/news-scanner.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now news-scanner.timer
  sudo cp caddy/news.caddy /etc/caddy/conf.d/news.caddy
  caddy validate --config /etc/caddy/Caddyfile
  sudo systemctl reload caddy
  ```

- **DNS:** an `A` record for `news` in Cloudflare, pointing at the same droplet IP as everything else.
- **One step lives outside this repo:** add a card linking to `news.lalutir.com` on the main site's homepage, in the separate `lalutir.com` repo, and deploy that repo once — per its own README's "Adding a new subdomain." Nothing else there needs to change.

## The newsletter registry (how the dropdown works)

`site/data/newsletters.json` lists every newsletter the dropdown can show — for now, one entry:

```json
[
  { "id": "politics-geopolitics", "label": "Politics & Geopolitics", "data": "data/politics-geopolitics/latest.json" }
]
```

`site/assets/js/site.js` reads this registry to populate the dropdown, and fetches whichever `data` path is selected. Each `latest.json` matches the shape the `publish` stage writes:

```json
{
  "newsletter_id": "politics-geopolitics",
  "generated_at": "2026-09-10T07:00:00+02:00",
  "run": "am",
  "briefing": "A few sentences synthesizing this run's items collectively.",
  "entries": [
    { "title": "…", "source": "NOS", "url": "https://…", "language": "nl", "published_at": "2026-09-10T06:42:00+02:00", "summary": "…" }
  ]
}
```

## Adding a page (`site/`)

New folder + `index.html` under `site/`, copy the `<head>`/nav/footer block from `site/index.html`, add the nav link to `nav-links` on every page — same zero-templating pattern as `lalutir.com` and `lalutir/template` itself.

## Adding a newsletter

Two moving parts, and they don't have to live in the same place:

1. Whatever produces the newsletter writes a `latest.json` matching the schema above, somewhere under `site/data/<id>/`.
2. Add a matching entry to `site/data/newsletters.json`. The dropdown picks it up automatically — no other code change needed.

If the new newsletter is produced by *this* repo (another Python module alongside `news_scanner/`), that's it. If it's produced by a genuinely separate project instead, that project can write into `site/data/<id>/` over SSH as part of its own deploy, the same way `world-cup-predictor` pushes its generated output into its own served directory today. Decide this when a second newsletter actually exists rather than guessing now.

## Adding a news source

New entry in `config/sources.yaml`: name, language, feed URL(s), paywall status. Check the paywall status by hand first — "has RSS" and "isn't paywalled" are two different facts. If a source is genuinely mixed, like AD, add a `filter` rule (see AD's `skip_field`/`skip_value` — its paid pieces are marked with a custom `dpp_paid` element, not an RSS `<category>`, so check what the *actual* feed does rather than assuming a generic pattern) rather than excluding the source outright.

## A few known tradeoffs

- **One repo for both halves.** Bundling the site into this repo, rather than its own (the droplet's usual pattern), keeps deploy to one script and means the site never reads across a repo boundary. The cost: this repo now mixes a Python backend with a static front-end, and its deploy script does more than either half would alone. If a second, differently-built newsletter shows up later, revisit whether it still belongs here.
- **Relevance filtering.** A plain keyword match (politics/war/conflict-adjacent terms) is cheap and predictable, but will miss nuance and let some noise through. Using Claude (Haiku is enough) to make the actual relevance call — and write the one-line description — costs a little per run but handles nuance and can bridge an NL headline for an English reader without a separate translation step. Built as both, not one or the other: `config/keywords.yaml` cuts obvious noise before anything reaches Haiku, which then makes the real call on survivors.
- **Cross-source duplication.** The same story often runs on several outlets. This starting design doesn't cluster near-duplicate stories across sources — it lists them as they arrive, grouped by source. Real clustering needs some notion of "same event" across two languages; treat it as a v2, not a blocker.
- **Translation.** Dutch headlines stay in Dutch by default, both in the email and on the site, so the digest reflects what the source actually published. Bilingual delivery is a Claude-assisted addition on top of this, not a redesign.

## When to commit

- Create commits after completing each logical unit of work.
- Do not push to the remote repository unless asked.
- Use conventional commit messages (e.g. "feat:", "fix:", "refactor:").