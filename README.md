# seaglass-template

A starting point for every future site: the Seaglass design system (soft, tinted glass — see `CLAUDE.md`) plus the minimum scaffolding to make it real — nav, footer, hero, a 404 page, the signature motion script. No framework, no build step, no dependencies beyond two Google Fonts.

This exists so "make it look like lalutir.com" is a five-minute starting point instead of a re-explanation every time.

## Turn this into a real GitHub template (one-time setup)

1. Push this folder as its own repo — e.g. `github.com/lalutir/seaglass-template`.
2. On GitHub: **Settings → General → Template repository** → check the box.
3. Done. Every future project starts from the green **Use this template** button on that repo's page (instead of **Code → Clone**), which creates a brand-new repo with this exact starting content and no shared git history.

## Using it for a new project

1. **Use this template** → name the new repo → clone it locally.
2. Open `CLAUDE.md` and fill in the blanks: project name, site map, infrastructure (hosting/deploy — copy the relevant section from `lalutir.com`'s `CLAUDE.md` if it's going on the same droplet), and anything that starts out as placeholder content.
3. Replace the bracketed `[placeholders]` in `index.html` and `404.html` with real copy.
4. Build out whatever additional pages the project needs, following the pattern in `CLAUDE.md`'s "Adding a page" section.
5. If the project needs its own subdomain off `lalutir.com`, follow the pattern documented in `lalutir.com`'s own `README.md` under "Adding a new subdomain" — own repo, own Caddy snippet, own deploy script, no changes needed to the main site.

## What's in here

```
.
├── CLAUDE.md              # design system rules + fill-in-the-blanks project sections
├── index.html             # minimal starter homepage
├── 404.html                # generic not-found page
└── assets/
    ├── css/
    │   ├── tokens.css      # the Seaglass palette/type/glass system — copy in unchanged
    │   └── site.css        # generic nav/footer/hero/section patterns — extend per project
    └── js/
        └── site.js         # mobile nav toggle + the signature motion (opt in via .glass-focus)
```

`tokens.css` is the one file that should never change between projects — it's the whole reason a new site inherits the look instantly instead of needing the aesthetic decided from scratch each time.
