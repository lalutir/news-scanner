"""Groups filtered items by underlying news story, not by source and not by
a merely shared subject.

Broader than "the exact same event": several angles on one ongoing story
(an anniversary ceremony, a survivor's reflection, and an official's
statement, all marking the same anniversary) belong in one cluster. But
items that just happen to share a subject or person while covering
genuinely different developments (two unrelated Trump stories) do not.
Also writes each cluster's combined summary, synthesized across every
source in it. See CLAUDE.md's "Cross-source duplication" tradeoff.

Only stories covered by at least two different outlets are kept. A story one
outlet alone reports is left out - and, to save output tokens, Sonnet is told
not to write a summary for it at all. Several articles from the same outlet
still count as one outlet.

A second, small Sonnet call then looks only at the finished topics and merges
any that still cover the same story (see merge_duplicate_topics).

One main Sonnet call per run. If that call comes back unusable (truncated,
malformed, or missing), the items are split in half and each half is
clustered separately, recursively, so a large backlog degrades to
slightly-less-merged clusters instead of taking the whole run down. A
failed run doesn't mark anything as sent, so without this the next run
would face an even bigger backlog and fail the same way - which is what
happened on 2026-09-15. (A split also means an outlet in one half can't be
matched with an outlet in the other; that story is left out as single-outlet.)
"""

import json

import anthropic

from news_scanner import settings  # noqa: F401 - loads .env as a side effect

CLUSTER_TOOL = {
    "name": "story_clusters",
    "description": (
        "Group news items into story clusters and write a combined summary "
        "for each cluster covered by at least two different outlets."
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
                                "given, of every item covering this story. "
                                "Items must come from at least two different "
                                "outlets."
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
    "Each item belongs to at most one cluster, and two clusters must never "
    "be about the same story - if they would be, make them one.\n\n"
    "Only return a cluster if at least two different outlets (the name in "
    "square brackets) cover it; several items from the same outlet count as "
    "a single outlet. Leave every other item out entirely - do not write a "
    "cluster or a summary for a story only one outlet covers.\n\n"
    "For each cluster, write the combined summary - one account synthesized "
    "across all of that cluster's sources, not a source-by-source recap. "
    "Items may be in English or Dutch - match and summarize by the "
    "underlying story, not by language or wording.\n\n"
)

MERGE_TOOL = {
    "name": "merge_duplicate_topics",
    "description": (
        "Merge groups of topics that cover the same underlying story into one "
        "topic each, with a combined summary."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "merges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": (
                                "0-based indices, from the numbered list "
                                "given, of two or more topics that are the "
                                "same story."
                            ),
                        },
                        "topic": {
                            "type": "string",
                            "description": (
                                "A specific, concrete label for the merged "
                                "story - never a broad subject."
                            ),
                        },
                        "summary": {
                            "type": "string",
                            "description": (
                                "3-5 sentences combining the summaries of "
                                "every topic in the group into one account of "
                                "the story - not a recap of each topic."
                            ),
                        },
                    },
                    "required": ["topic_indices", "topic", "summary"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["merges"],
        "additionalProperties": False,
    },
}

_MERGE_PROMPT = (
    "Below are the topics of a news digest, each with its summary. Some may "
    "be about the same underlying story and belong together as a single "
    "topic - e.g. 'Gaza ceasefire talks resume in Cairo' and 'Hamas "
    "delegation arrives for ceasefire negotiations' are one story seen from "
    "two angles. Topics are NOT the same story just because they share a "
    "person, country or subject: 'Trump renews push to annex Greenland' and "
    "'Trump announces new steel tariffs' stay separate.\n\n"
    "Return one entry per group of two or more topics that are the same "
    "story: their indices, one topic label, and one combined summary "
    "synthesized across the whole group. Leave out any topic that is not "
    "part of such a group. If no topics overlap, return an empty list.\n\n"
)

# A merge entry is a label plus a 3-5 sentence summary, ~200 tokens; this is
# room for dozens of merges and is only a ceiling, not a cost.
MERGE_MAX_OUTPUT_TOKENS = 8000

# Each cluster costs roughly 150 output tokens (label, 3-5 sentence summary,
# index list). The old cap of 8000 covered ~55 clusters and was cut off on a
# 151-item backlog. 32000 leaves room for several days of backlog; streaming
# keeps a long response from tripping the SDK's non-streaming timeout.
MAX_OUTPUT_TOKENS = 32000

# A failed batch smaller than this isn't split again - its items are left
# unjudged and retried on the next run.
MIN_SPLIT_SIZE = 8

# A story needs coverage from at least this many different outlets.
MIN_OUTLETS = 2


class ClusterResponseError(RuntimeError):
    """Sonnet's reply was unusable: truncated, missing, or malformed."""


def _outlets(items):
    return {item["source"] for item in items}


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

    return _tool_list(message, "clusters", MAX_OUTPUT_TOKENS)


def _tool_list(message, field, max_tokens):
    """The array `field` from a forced tool call's reply, or
    ClusterResponseError if the reply can't be trusted."""
    if message.stop_reason == "max_tokens":
        raise ClusterResponseError(
            f"response truncated at {max_tokens} output tokens"
        )
    tool_use = next((b for b in message.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise ClusterResponseError(
            f"no tool_use block (stop_reason={message.stop_reason})"
        )

    value = tool_use.input.get(field) if isinstance(tool_use.input, dict) else None
    if isinstance(value, str):
        # Pre-strict quirk, kept as a belt-and-braces path: the whole payload
        # as a JSON-encoded string.
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ClusterResponseError(f"{field} field is not valid JSON: {exc}") from exc
        if isinstance(value, dict):
            value = value.get(field)
    if not isinstance(value, list):
        raise ClusterResponseError(
            f"{field} field is {type(value).__name__}, not a list"
        )
    return value


def _assemble(items, raw_clusters):
    """Turn Sonnet's index lists into clusters of the original item dicts.
    Returns (clusters, uncorroborated). A cluster is only kept if its items
    span at least MIN_OUTLETS outlets - Sonnet is told to leave single-outlet
    stories out, but that's enforced here rather than trusted. An index Sonnet
    used twice stays with the first cluster that claimed it, and everything
    not in a kept cluster is returned as uncorroborated."""
    clusters = []
    claimed = set()
    for cluster in raw_clusters:
        if not isinstance(cluster, dict) or not cluster.get("topic"):
            continue
        indices = [
            i for i in cluster.get("item_indices", [])
            if isinstance(i, int) and 0 <= i < len(items) and i not in claimed
        ]
        members = [items[i] for i in indices]
        if len(_outlets(members)) < MIN_OUTLETS:
            continue
        claimed.update(indices)
        clusters.append({
            "topic": cluster["topic"],
            "summary": cluster.get("summary", ""),
            "items": members,
        })

    uncorroborated = [item for i, item in enumerate(items) if i not in claimed]
    return clusters, uncorroborated


def _cluster_or_split(client, items):
    """Returns (clusters, uncorroborated) for this batch. Items of a batch
    that failed beyond splitting appear in neither: they were never judged,
    so the caller must leave them alone to be retried on the next run."""
    try:
        raw = _request_clusters(client, items)
    except ClusterResponseError as exc:
        if len(items) < MIN_SPLIT_SIZE:
            print(
                f"  clustering {len(items)} items failed ({exc}); "
                "leaving them for the next run"
            )
            return [], []
        half = len(items) // 2
        print(
            f"  clustering {len(items)} items failed ({exc}); "
            f"retrying as two batches of {half} and {len(items) - half}"
        )
        first_clusters, first_left = _cluster_or_split(client, items[:half])
        second_clusters, second_left = _cluster_or_split(client, items[half:])
        return first_clusters + second_clusters, first_left + second_left
    return _assemble(items, raw)


def _request_merges(client, clusters):
    """One merge call over the finished topics. Returns the raw merge list, or
    raises ClusterResponseError if the reply can't be trusted."""
    listing = "\n".join(
        f"{i}. {cluster['topic']}: {cluster['summary']}"
        for i, cluster in enumerate(clusters)
    )
    message = client.messages.create(
        model=settings.CLUSTER_MODEL,
        max_tokens=MERGE_MAX_OUTPUT_TOKENS,
        tools=[MERGE_TOOL],
        tool_choice={"type": "tool", "name": "merge_duplicate_topics"},
        messages=[{"role": "user", "content": _MERGE_PROMPT + listing}],
    )
    return _tool_list(message, "merges", MERGE_MAX_OUTPUT_TOKENS)


def _apply_merges(clusters, merges):
    """Fold each merge group into one cluster, placed where its first member
    was. A topic already claimed by an earlier merge is ignored, and a group
    left with fewer than two valid topics is skipped, so a sloppy reply can
    only under-merge, never lose or duplicate an item."""
    absorbed = set()
    replacement = {}
    for merge in merges:
        if not isinstance(merge, dict):
            continue
        indices = sorted({
            i for i in merge.get("topic_indices", [])
            if isinstance(i, int) and 0 <= i < len(clusters) and i not in absorbed
        })
        if len(indices) < 2:
            continue
        members = [clusters[i] for i in indices]
        absorbed.update(indices)
        replacement[indices[0]] = {
            "topic": merge.get("topic") or members[0]["topic"],
            "summary": merge.get("summary") or members[0]["summary"],
            "items": [item for member in members for item in member["items"]],
        }

    result = []
    for i, cluster in enumerate(clusters):
        if i in replacement:
            result.append(replacement[i])
        elif i not in absorbed:
            result.append(cluster)
    return result


def merge_duplicate_topics(clusters, client):
    """Second pass: fold topics that still cover the same story into one. The
    clustering call can emit near-duplicate clusters, and when a big backlog
    is split in half each half is clustered blind to the other. This pass sees
    only the finished topics, so it's a small, much easier job than clustering.

    It's a refinement, so a failure here (unusable reply, API outage after the
    SDK's retries) keeps the clusters as they are rather than failing the run:
    a failed run marks nothing as sent, which would throw away the Haiku and
    clustering spend that already happened."""
    if len(clusters) < 2:
        return clusters
    try:
        merges = _request_merges(client, clusters)
    except (ClusterResponseError, anthropic.APIError) as exc:
        print(f"  merging duplicate topics failed ({exc}); keeping topics as clustered")
        return clusters
    merged = _apply_merges(clusters, merges)
    if len(merged) < len(clusters):
        print(f"  merged {len(clusters) - len(merged)} duplicate topic(s)")
    return merged


def cluster_items(items, client=None):
    """Returns (clusters, uncorroborated).

    clusters: [{"topic", "summary", "items"}, ...] - one per story that at
    least two different outlets cover, "items" being the original item dicts.
    No two clusters should be about the same story (see merge_duplicate_topics).
    uncorroborated: items judged to be covered by a single outlet, left out of
    the digest. Items from a batch that failed even after splitting are in
    neither list - they weren't judged, so they get retried next run."""
    if len(_outlets(items)) < MIN_OUTLETS:
        # Nothing to corroborate against - skip the API call entirely.
        return [], list(items)

    client = client or anthropic.Anthropic()
    clusters, uncorroborated = _cluster_or_split(client, items)
    return merge_duplicate_topics(clusters, client), uncorroborated
