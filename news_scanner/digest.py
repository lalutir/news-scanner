"""Compiles the HTML + plaintext digest email.

Grouped by source, no cross-source clustering (see CLAUDE.md's "Cross-source
duplication" tradeoff - that's a v2). Each entry links to the original
article; only a headline and the filter stage's one-line summary go in the
body, never full article text.
"""

from html import escape

import anthropic

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

BRIEFING_TOOL = {
    "name": "daily_briefing",
    "description": (
        "Write a short daily-briefing paragraph summarizing a set of news "
        "items collectively."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "briefing": {
                "type": "string",
                "description": (
                    "3-5 sentences giving a reader the shape of this run's "
                    "news at a glance - the throughlines and most significant "
                    "developments across all items, in plain English. Not a "
                    "headline-by-headline recap; the entries below already "
                    "list those individually."
                ),
            },
        },
        "required": ["briefing"],
    },
}


def generate_briefing(items, client=None):
    """One Haiku call synthesizing this run's items into a short top-of-digest
    paragraph. Returns "" if there's nothing to summarize."""
    if not items:
        return ""
    client = client or anthropic.Anthropic()
    listing = "\n".join(
        f"- [{item['source']}] {item['title']}: {item['summary']}" for item in items
    )
    message = client.messages.create(
        model=settings.HAIKU_MODEL,
        max_tokens=300,
        tools=[BRIEFING_TOOL],
        tool_choice={"type": "tool", "name": "daily_briefing"},
        messages=[{
            "role": "user",
            "content": (
                f"Today's politics/geopolitics/conflict items:\n\n{listing}\n\n"
                "Write the daily briefing."
            ),
        }],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input["briefing"]
    raise RuntimeError("Haiku did not return a tool_use block")


def _group_by_source(items):
    grouped = {}
    for item in items:
        grouped.setdefault(item["source"], []).append(item)
    return grouped


def compile_html(items, briefing):
    grouped = _group_by_source(items)
    sections = []
    for source, source_items in grouped.items():
        entries_html = "\n".join(
            "<li style=\"margin-bottom:0.75em;\">"
            f'<a href="{escape(item["url"])}">{escape(item["title"])}</a>'
            f'<p style="margin:0.2em 0 0; color:#444;">{escape(item["summary"])}</p>'
            "</li>"
            for item in source_items
        )
        sections.append(
            f'<h2 style="font-size:1.05em; margin:1.5em 0 0.5em;">{escape(source)}</h2>\n'
            f'<ul style="padding-left:1.2em; margin:0;">\n{entries_html}\n</ul>'
        )
    body = "\n".join(sections)
    briefing_html = (
        f'<p style="font-size:1.05em; margin-bottom:1.5em;">{escape(briefing)}</p>'
        if briefing else ""
    )
    return (
        '<!DOCTYPE html><html><body style="font-family:sans-serif; '
        'max-width:640px; margin:0 auto; color:#111;">'
        f"{briefing_html}{body}"
        "</body></html>"
    )


def compile_text(items, briefing):
    grouped = _group_by_source(items)
    lines = []
    if briefing:
        lines += [briefing, ""]
    for source, source_items in grouped.items():
        lines.append(source)
        lines.append("-" * len(source))
        for item in source_items:
            lines.append(item["title"])
            lines.append(f"  {item['summary']}")
            lines.append(f"  {item['url']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
