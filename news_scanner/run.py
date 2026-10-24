"""One full fetch -> dedupe -> filter -> cluster -> digest -> send -> publish
cycle.

Dedupe runs before the Claude filter, not after, so items already sent in
an earlier digest never get re-summarized - most of a feed's entries are
still there from the previous run, and Haiku is the costly step.

Only stories at least two outlets cover make the digest. A single-outlet item
is held over (see dedupe.HOLD_RUNS) and rejoins the next runs' clustering, so a
second outlet that picks the story up later still matches it; if none does, it
is skipped for good. Items Haiku rejects are skipped too. Either way later runs
never pay to judge an item again. If nothing qualifies, no email goes out.

Runs at 07:00 and 19:00 Europe/Amsterdam via systemd/news-scanner.timer.
"""

import argparse

from news_scanner import settings  # noqa: F401 - loads .env as a side effect
from news_scanner.cluster import cluster_items
from news_scanner.dedupe import dedupe, hold, load_held, mark_sent, mark_skipped
from news_scanner.digest import compile_html, compile_text, generate_briefing
from news_scanner.fetch import fetch_all
from news_scanner.filter import filter_items
from news_scanner.publish import current_run, publish
from news_scanner.send import send_digest


def run(dry_run=False):
    print("Fetching feeds...")
    items = fetch_all()
    print(f"  {len(items)} items fetched")

    print("Deduping against sent history...")
    unseen = dedupe(items)
    print(f"  {len(unseen)} unseen items ({len(items) - len(unseen)} already handled, dropped before filtering)")

    print("Filtering for relevance...")
    relevant, rejected = filter_items(unseen)
    print(f"  {len(relevant)} items judged relevant ({len(rejected)} rejected by Haiku)")

    # Single-outlet items from earlier runs, already judged, get another chance
    # to find a second outlet among today's items.
    held = load_held()
    print(f"  {len(held)} single-outlet items held over from earlier runs")

    print("Grouping into story clusters...")
    clusters, uncorroborated = cluster_items(held + relevant)
    print(
        f"  {len(clusters)} stories covered by two or more outlets "
        f"({len(uncorroborated)} single-outlet items still waiting for a second)"
    )

    print("Generating daily briefing...")
    briefing = generate_briefing(clusters)

    run_label = current_run()

    if dry_run:
        # Nothing reaches an inbox or the site on a dry run - see README's
        # "Getting started" step 3.
        print("\nDry run - not sending or publishing. Digest would read:\n")
        print(compile_text(clusters, briefing))
        if uncorroborated:
            print("Not included yet (only one outlet covers them so far):")
            for item in uncorroborated:
                print(f"- [{item['source']}] {item['title']}")
        return clusters

    if clusters:
        subject = f"Politics & Geopolitics digest - {run_label.upper()}"
        html = compile_html(clusters, briefing)
        text = compile_text(clusters, briefing)

        print(f"Sending digest to {settings.DIGEST_RECIPIENTS}...")
        send_digest(subject, html, text)
        mark_sent([item for cluster in clusters for item in cluster["items"]])
        print("Sent.")
    else:
        # Single-outlet items are dropped now, so a quiet run can end up with
        # nothing - don't email a blank digest. The site still gets published
        # below; it renders an empty run as "No new stories in this run."
        print("No story is covered by two or more outlets - not sending an email.")
    hold(uncorroborated)
    mark_skipped(rejected)

    print("Publishing to site/data...")
    publish(clusters, briefing, run=run_label)
    print("Done.")

    return clusters


def main():
    parser = argparse.ArgumentParser(description="Run one news-scanner digest cycle.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip sending and publishing; print the digest that would go out.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
