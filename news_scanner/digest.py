"""Compiles the HTML + plaintext digest email.

Grouped by story cluster (see news_scanner/cluster.py and CLAUDE.md's
"Cross-source duplication" tradeoff), not by source: each topic gets one
summary combining every source that covers it - not a per-source recap -
followed by a numbered, IEEE-style reference list linking out to each
original article. Never full article text.
"""

from html import escape

import anthropic

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

BRIEFING_TOOL = {
    "name": "daily_briefing",
    "description": (
        "Write a daily-briefing paragraph summarizing a set of news stories "
        "collectively."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "briefing": {
                "type": "string",
                "description": (
                    "6-8 sentences giving a reader the shape of this run's "
                    "news at a glance - the throughlines and most significant "
                    "developments across all topics, in plain English. Not a "
                    "topic-by-topic recap; the sections below already cover "
                    "those individually."
                ),
            },
        },
        "required": ["briefing"],
    },
}


def generate_briefing(clusters, client=None):
    """One Haiku call synthesizing this run's clusters into a top-of-digest
    paragraph. Returns "" if there's nothing to summarize."""
    if not clusters:
        return ""
    client = client or anthropic.Anthropic()
    listing = "\n".join(f"- {c['topic']}: {c['summary']}" for c in clusters)
    message = client.messages.create(
        model=settings.HAIKU_MODEL,
        max_tokens=500,
        tools=[BRIEFING_TOOL],
        tool_choice={"type": "tool", "name": "daily_briefing"},
        messages=[{
            "role": "user",
            "content": (
                f"Today's politics/geopolitics/conflict stories:\n\n{listing}\n\n"
                "Write the daily briefing."
            ),
        }],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input["briefing"]
    raise RuntimeError("Haiku did not return a tool_use block")


def compile_html(clusters, briefing):
    sections = []
    for cluster in clusters:
        refs_html = "\n".join(
            f'<li><a href="{escape(item["url"])}">[{i}] {escape(item["source"])}, '
            f'&ldquo;{escape(item["title"])}&rdquo;</a></li>'
            for i, item in enumerate(cluster["items"], start=1)
        )
        sections.append(
            f'<h2 style="font-size:1.05em; margin:1.5em 0 0.5em;">{escape(cluster["topic"])}</h2>\n'
            f'<p style="margin:0 0 0.6em; color:#333;">{escape(cluster["summary"])}</p>\n'
            f'<ol style="padding-left:1.2em; margin:0; font-size:0.85em; color:#666;">\n{refs_html}\n</ol>'
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


def compile_text(clusters, briefing):
    lines = []
    if briefing:
        lines += [briefing, ""]
    for cluster in clusters:
        lines.append(cluster["topic"])
        lines.append("-" * len(cluster["topic"]))
        lines.append(cluster["summary"])
        for i, item in enumerate(cluster["items"], start=1):
            lines.append(f'  [{i}] {item["source"]}, "{item["title"]}" - {item["url"]}')
        lines.append("")
    return "\n".join(lines).strip() + "\n"
