"""Groups filtered items by underlying news story, not by source and not by
a merely shared subject.

Broader than "the exact same event": several angles on one ongoing story
(an anniversary ceremony, a survivor's reflection, and an official's
statement, all marking the same anniversary) belong in one cluster. But
items that just happen to share a subject or person while covering
genuinely different developments (two unrelated Trump stories) do not.
Also writes each cluster's combined summary, synthesized across every
source in it. See CLAUDE.md's "Cross-source duplication" tradeoff.

One Sonnet call per run. If that call comes back unusable (truncated,
malformed, or missing), the items are split in half and each half is
clustered separately, recursively, so a large backlog degrades to
slightly-less-merged clusters instead of taking the whole run down. A
failed run doesn't mark anything as sent, so without this the next run
would face an even bigger backlog and fail the same way - which is what
happened on 2026-09-15.
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
    # strict: the API guarantees `input` matches this schema exactly. Without
    # it, "clusters" occasionally arrived as a JSON-encoded string instead of
    # an array - and one of those strings had a bad quote in it.
    "strict": True,
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
                    "additionalProperties": False,
                },
            },
        },
        "required": ["clusters"],
        "additionalProperties": False,
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

# Each cluster costs roughly 150 output tokens (label, 3-5 sentence summary,
# index list). The old cap of 8000 covered ~55 clusters and was cut off on a
# 151-item backlog. 32000 leaves room for several days of backlog; streaming
# keeps a long response from tripping the SDK's non-streaming timeout.
MAX_OUTPUT_TOKENS = 32000

# A failed batch smaller than this isn't split again - its items just become
# single-item clusters.
MIN_SPLIT_SIZE = 8


class ClusterResponseError(RuntimeError):
    """Sonnet's reply was unusable: truncated, missing, or malformed."""


def _single(item):
    return {"topic": item["title"], "summary": item["summary"], "items": [item]}


def _request_clusters(client, items):
    """One clustering call. Returns the raw cluster list Sonnet produced, or
    raises ClusterResponseError if the reply can't be trusted. API errors
    (rate limits, outages) propagate as-is - those are for the SDK's own
    retries and, failing that, the next scheduled run."""
    listing = "\n".join(
        f"{i}. [{item['source']}] {item['title']}: {item['summary']}"
        for i, item in enumerate(items)
    )
    try:
        with client.messages.stream(
            model=settings.CLUSTER_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            tools=[CLUSTER_TOOL],
            tool_choice={"type": "tool", "name": "story_clusters"},
            messages=[{"role": "user", "content": _PROMPT + listing}],
        ) as stream:
            message = stream.get_final_message()
    except ValueError as exc:
        # The SDK raises ValueError when the tool input isn't parseable JSON
        # at all; anything API-shaped is an anthropic.APIError, not this.
        raise ClusterResponseError(f"unparseable tool input: {exc}") from exc

    if message.stop_reason == "max_tokens":
        raise ClusterResponseError(
            f"response truncated at {MAX_OUTPUT_TOKENS} output tokens"
        )
    tool_use = next((b for b in message.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise ClusterResponseError(
            f"no tool_use block (stop_reason={message.stop_reason})"
        )

    clusters = tool_use.input.get("clusters") if isinstance(tool_use.input, dict) else None
    if isinstance(clusters, str):
        # Pre-strict quirk, kept as a belt-and-braces path: the whole payload
        # as a JSON-encoded string.
        try:
            clusters = json.loads(clusters)
        except json.JSONDecodeError as exc:
            raise ClusterResponseError(f"clusters field is not valid JSON: {exc}") from exc
        if isinstance(clusters, dict):
            clusters = clusters.get("clusters")
    if not isinstance(clusters, list):
        raise ClusterResponseError(
            f"clusters field is {type(clusters).__name__}, not a list"
        )
    return clusters


def _assemble(items, raw_clusters):
    """Turn Sonnet's index lists into clusters of the original item dicts.
    Every item lands in exactly one cluster: an index Sonnet used twice
    stays with the first cluster that claimed it, and anything it skipped
    becomes a cluster of one."""
    result = []
    claimed = set()
    for cluster in raw_clusters:
        if not isinstance(cluster, dict) or not cluster.get("topic"):
            continue
        indices = [
            i for i in cluster.get("item_indices", [])
            if isinstance(i, int) and 0 <= i < len(items) and i not in claimed
        ]
        if not indices:
            continue
        claimed.update(indices)
        result.append({
            "topic": cluster["topic"],
            "summary": cluster.get("summary", ""),
            "items": [items[i] for i in indices],
        })

    for i, item in enumerate(items):
        if i not in claimed:
            result.append(_single(item))
    return result


def _cluster_or_split(client, items):
    try:
        raw = _request_clusters(client, items)
    except ClusterResponseError as exc:
        if len(items) < MIN_SPLIT_SIZE:
            print(
                f"  clustering {len(items)} items failed ({exc}); "
                "keeping them as single-item clusters"
            )
            return [_single(item) for item in items]
        half = len(items) // 2
        print(
            f"  clustering {len(items)} items failed ({exc}); "
            f"retrying as two batches of {half} and {len(items) - half}"
        )
        return (
            _cluster_or_split(client, items[:half])
            + _cluster_or_split(client, items[half:])
        )
    return _assemble(items, raw)


def cluster_items(items, client=None):
    """Returns a list of clusters: [{"topic", "summary", "items"}, ...],
    where "items" are the original item dicts belonging to that cluster.
    Every input item ends up in exactly one cluster."""
    if not items:
        return []
    if len(items) == 1:
        return [_single(items[0])]

    client = client or anthropic.Anthropic()
    return _cluster_or_split(client, items)
