"""Groups filtered items by underlying news story, not by source and not by
a merely shared subject.

Broader than "the exact same event": several angles on one ongoing story
(an anniversary ceremony, a survivor's reflection, and an official's
statement, all marking the same anniversary) belong in one cluster. But
items that just happen to share a subject or person while covering
genuinely different developments (two unrelated Trump stories) do not.
Also writes each cluster's combined summary, synthesized across every
source in it. See CLAUDE.md's "Cross-source duplication" tradeoff.
"""

import json

import anthropic

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

CLUSTER_TOOL = {
    "name": "story_clusters",
    "description": (
        "Group news items into story clusters and write a combined summary "
        "for each cluster."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": (
                                "A specific, concrete label for this story - "
                                "e.g. 'Trump renews push to annex Greenland', "
                                "never a broad subject like 'Trump' or 'US "
                                "politics'."
                            ),
                        },
                        "summary": {
                            "type": "string",
                            "description": (
                                "3-5 sentences synthesizing what happened, "
                                "combining every source in this cluster into "
                                "one account of the story - not a recap of "
                                "each source in turn."
                            ),
                        },
                        "item_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": (
                                "0-based indices, from the numbered list "
                                "given, of every item covering this story."
                            ),
                        },
                    },
                    "required": ["topic", "summary", "item_indices"],
                },
            },
        },
        "required": ["clusters"],
    },
}

_PROMPT = (
    "Group these news items into story clusters - items covering the same "
    "underlying news story or development, even if they cover different "
    "angles, statements, or moments within it. For example, several items "
    "marking the same anniversary from different angles (an official "
    "ceremony, survivor reflections, a leader's statement) belong in one "
    "cluster together. But don't lump items together just because they "
    "share a subject or person if they're actually about different "
    "developments: 'Trump renews push to annex Greenland' and 'Denmark "
    "rejects Trump's Greenland remarks' belong together (same story, "
    "different angles); 'Trump renews push to annex Greenland' and 'Trump "
    "announces new steel tariffs' do not (same person, unrelated stories). "
    "Every item must end up in exactly one cluster, including a cluster of "
    "one if nothing else covers that story. Then write each cluster's "
    "combined summary - one account synthesized across all of that "
    "cluster's sources, not a source-by-source recap. Items may be in "
    "English or Dutch - match and summarize by the underlying story, not by "
    "language or wording.\n\n"
)


def cluster_items(items, client=None):
    """Returns a list of clusters: [{"topic", "summary", "items"}, ...],
    where "items" are the original item dicts belonging to that cluster.
    Every input item ends up in exactly one cluster."""
    if not items:
        return []
    if len(items) == 1:
        item = items[0]
        return [{"topic": item["title"], "summary": item["summary"], "items": [item]}]

    client = client or anthropic.Anthropic()
    listing = "\n".join(
        f"{i}. [{item['source']}] {item['title']}: {item['summary']}"
        for i, item in enumerate(items)
    )
    message = client.messages.create(
        model=settings.CLUSTER_MODEL,
        max_tokens=8000,
        tools=[CLUSTER_TOOL],
        tool_choice={"type": "tool", "name": "story_clusters"},
        messages=[{"role": "user", "content": _PROMPT + listing}],
    )
    for block in message.content:
        if block.type == "tool_use":
            clusters = block.input.get("clusters")
            break
    else:
        raise RuntimeError("Claude did not return a tool_use block")

    # Occasionally comes back as a JSON-encoded string instead of the
    # array the schema asked for - tolerate it rather than crash.
    if isinstance(clusters, str):
        clusters = json.loads(clusters).get("clusters", [])

    result = []
    claimed = set()
    for cluster in clusters:
        indices = cluster.get("item_indices", [])
        members = [items[i] for i in indices if 0 <= i < len(items)]
        if not members:
            continue
        claimed.update(indices)
        result.append({
            "topic": cluster["topic"],
            "summary": cluster.get("summary", ""),
            "items": members,
        })

    # Anything Claude missed still needs to show up somewhere.
    for i, item in enumerate(items):
        if i not in claimed:
            result.append({
                "topic": item["title"],
                "summary": item["summary"],
                "items": [item],
            })

    return result
