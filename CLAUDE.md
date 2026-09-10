# [Project name]

[One sentence: what this site/project is.] Design system is **Seaglass** — soft, tinted glass. Read this whole file before touching any page.

## Site map

<!-- Fill in as pages get built. Keep this current — it's the fastest way
     for a fresh Claude Code session to understand the project. -->

| Path | Purpose | Status |
|---|---|---|
| `/` | Home | Real |

## What's placeholder

<!-- List anything in the codebase that's a stand-in for real content —
     bio text, sample data, a contact email — so nobody mistakes a draft
     for done. Delete a line once the real thing replaces it. -->

## Design system — Seaglass

Tumbled sea glass, not "frosted UI glass." Frosted, tinted, never perfectly clear, edges softened rather than sharp — glass with a history, not a filter effect. Deliberately **not**: cream-plus-serif-plus-terracotta, near-black-plus-one-acid-accent, or plain white/grey iOS-style glass — the three defaults AI-generated design tends to land on.

Non-negotiable rules:
- Reference tokens only (`assets/css/tokens.css`). Never hardcode a hex, `rgba()`, or px spacing in a page or in `site.css`.
- Glass is always tinted (`--glass-tint-*`) — never plain white/grey translucent.
- `--cobalt-rare` appears **once per screen, max**, for decorative/accent use (a CTA, a highlight). Its scarcity is the point. **Exception:** if a project needs a small set of *functional* categorical colors (e.g. status indicators, data-series colors), those are a deliberate, separate extension of the palette — add named tokens for them (e.g. `--status-warning`), document why in this file, and don't treat that as "spending" the cobalt-rare rule. The two are different jobs: cobalt-rare is for drawing the eye once; functional colors are for consistent, repeated meaning.
- Respect `prefers-reduced-motion` *and* `prefers-reduced-transparency` — both are already handled in `tokens.css`.
- Display type (Fraunces) is forced to its low-`opsz` cut (`font-variation-settings: 'opsz' 12`) even at large sizes — left on auto it snaps to a tighter, higher-contrast cut, which fights the soft concept. Already set on `h1, h2, h3` in `site.css`; keep it that way on any new heading style.
- Signature motion (hero glow follows the pointer; anything marked `.glass-focus` sharpens into view on scroll) lives in `assets/js/site.js`. Add `.glass-focus` to showcase moments only — not every card on a page. Restraint is the point.

Anti-patterns: numbered 01/02/03 markers unless content is a genuine sequence; more than one hero-style gradient per page; cards covering every inch of the `--sand` background.

## Infrastructure

<!-- Fill in: hosting, deploy mechanism, build step (or lack of one), any
     quirks worth not relearning by trial and error. Copy the relevant
     parts from lalutir.com's CLAUDE.md if this project shares the same
     droplet/Caddy setup. -->

## Adding a page

New folder + `index.html`, copy the `<head>`/nav/footer block from an existing page, add the nav link to `nav-links` **on every page** (no templating in this starter — see tradeoff below) and mark `aria-current="page"` only on the matching page.

## A known tradeoff

Nav and footer are duplicated by hand across pages rather than templated, to keep this a genuinely zero-build-step starting point. If that gets painful as the page count grows, the natural next step is a light static site generator (Eleventy, for instance) or a small script that stitches shared partials at commit time.

## When to commit

- Create commits after completing each logical unit of work.
- Do not push to the remote repository unless asked.
- Use conventional commit messages (e.g. "feat:", "fix:", "refactor:").