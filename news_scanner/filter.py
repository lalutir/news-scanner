"""Relevance filtering: a cheap keyword pre-filter, then Claude Haiku for
the final call and the one-line summary. See CLAUDE.md's filtering
tradeoff - this combines both options instead of picking one."""

from pathlib import Path

import anthropic
import yaml

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

KEYWORDS_PATH = Path(__file__).resolve().parent.parent / "config" / "keywords.yaml"

RELEVANCE_TOOL = {
    "name": "relevance_verdict",
    "description": (
        "Judge whether a news item belongs in a politics/geopolitics/conflict "
        "digest and, if so, write its one-line summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "relevant": {
                "type": "boolean",
                "description": (
                    "True only if this is genuinely about politics, geopolitics, "
                    "war, or conflict - national or international. Not general "
                    "news, sport, or entertainment, unless the story is genuinely "
                    "about politics or conflict within one of those beats."
                ),
            },
            "summary": {
                "type": "string",
                "description": (
                    "One or two plain sentences describing the story, for a "
                    "reader who hasn't read the article - written in English "
                    "regardless of the source's language (bridge a Dutch "
                    "headline, don't just translate it word for word). Empty "
                    "string if not relevant."
                ),
            },
        },
        "required": ["relevant", "summary"],
    },
}


def load_keywords(path=KEYWORDS_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def keyword_prefilter(items, keywords=None):
    """Cheap first pass: keep only items whose title or summary contain at
    least one configured politics/war/conflict-adjacent term. Cuts the
    volume that reaches Claude before the real (and costlier) relevance
    call."""
    keywords = keywords or load_keywords()
    terms = [term.lower() for lang_terms in keywords.values() for term in lang_terms]
    survivors = []
    for item in items:
        haystack = f"{item['title']} {item['raw_summary']}".lower()
        if any(term in haystack for term in terms):
            survivors.append(item)
    return survivors


def _judge(client, item):
    message = client.messages.create(
        model=settings.HAIKU_MODEL,
        max_tokens=300,
        tools=[RELEVANCE_TOOL],
        tool_choice={"type": "tool", "name": "relevance_verdict"},
        messages=[{
            "role": "user",
            "content": (
                f"Source: {item['source']} ({item['language']})\n"
                f"Title: {item['title']}\n"
                f"Description: {item['raw_summary']}\n\n"
                "Judge relevance for a politics/geopolitics/conflict news "
                "digest and write the summary."
            ),
        }],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Haiku did not return a tool_use block")


def claude_filter(items, client=None):
    """Final relevance call + one-line summary for every keyword survivor."""
    client = client or anthropic.Anthropic()
    results = []
    for item in items:
        verdict = _judge(client, item)
        if verdict.get("relevant"):
            results.append({**item, "summary": verdict["summary"]})
    return results


def filter_items(items, keywords=None, client=None):
    """Full two-stage filter: keyword pre-filter, then Claude Haiku."""
    survivors = keyword_prefilter(items, keywords)
    return claude_filter(survivors, client)


if __name__ == "__main__":
    from news_scanner.fetch import fetch_all

    all_items = fetch_all()
    survivors = keyword_prefilter(all_items)
    print(f"{len(all_items)} fetched, {len(survivors)} survive the keyword pre-filter")
    relevant = claude_filter(survivors)
    print(f"{len(relevant)} judged relevant by Claude")
    for item in relevant[:10]:
        print(f"- [{item['source']}] {item['title']}\n  {item['summary']}")
