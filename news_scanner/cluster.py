"""Groups filtered items by specific story, not by source or broad subject.

"Trump proposes annexing Greenland" is a cluster; "Trump" is not - every
item mentioning a shared name/subject doesn't belong together unless
they're covering the same concrete real-world event or development. See
CLAUDE.md's "Cross-source duplication" tradeoff.
"""

import json

import anthropic

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

CLUSTER_TOOL = {
    "name": "story_clusters",
    "description": (
        "Group news items into specific story clusters - items covering the "
        "exact same real-world event or development, not just a shared "
        "broad subject."
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
                                "A specific, concrete label for this exact "
                                "story - e.g. 'Trump proposes annexing "
                                "Greenland', never a broad subject like "
                                "'Trump' or 'US politics'."
                            ),
                        },
                        "item_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": (
                                "0-based indices, from the numbered list "
                                "given, of every item covering this specific "
                                "story."
                            ),
                        },
                    },
                    "required": ["topic", "item_indices"],
                },
            },
        },
        "required": ["clusters"],
    },
}

_PROMPT = (
    "Group these news items into specific story clusters - items covering "
    "the exact same real-world event or development, not just a shared "
    "broad subject (every item mentioning \"Trump\" is not one cluster; "
    "\"Trump proposes annexing Greenland\" is a cluster, and a separate "
    "Trump story is a different cluster). Every item must end up in exactly "
    "one cluster, including a cluster of one if nothing else covers that "
    "story. Items may be in English or Dutch - match by the underlying "
    "event, not by language or wording.\n\n"
)


def assign_topics(items, client=None):
    """Adds a 'topic' field to every item: a specific, concrete story label
    shared by every item covering the same event. Returns a new list of
    dicts; doesn't mutate the input."""
    if not items:
        return []
    if len(items) == 1:
        return [{**items[0], "topic": items[0]["title"]}]

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

    topic_by_index = {}
    for cluster in clusters:
        for i in cluster["item_indices"]:
            topic_by_index[i] = cluster["topic"]

    return [
        {**item, "topic": topic_by_index.get(i, item["title"])}
        for i, item in enumerate(items)
    ]
