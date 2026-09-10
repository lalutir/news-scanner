"""One full fetch -> filter -> dedupe -> digest -> send -> publish cycle.

Runs at 07:00 and 19:00 Europe/Amsterdam via systemd/news-scanner.timer.
"""

import argparse

from news_scanner import settings  # noqa: F401 - loads .env as a side effect
from news_scanner.dedupe import dedupe, mark_sent
from news_scanner.digest import compile_html, compile_text, generate_briefing
from news_scanner.fetch import fetch_all
from news_scanner.filter import filter_items
from news_scanner.publish import current_run, publish
from news_scanner.send import send_digest


def run(dry_run=False):
    print("Fetching feeds...")
    items = fetch_all()
    print(f"  {len(items)} items fetched")

    print("Filtering for relevance...")
    relevant = filter_items(items)
    print(f"  {len(relevant)} items judged relevant")

    print("Deduping against sent history...")
    fresh = dedupe(relevant)
    print(f"  {len(fresh)} fresh items after dedupe")

    print("Generating daily briefing...")
    briefing = generate_briefing(fresh)

    run_label = current_run()

    if dry_run:
        # Nothing reaches an inbox or the site on a dry run - see README's
        # "Getting started" step 3.
        print("\nDry run - not sending or publishing. Digest would read:\n")
        print(compile_text(fresh, briefing))
        return fresh

    subject = f"Politics & Geopolitics digest - {run_label.upper()}"
    html = compile_html(fresh, briefing)
    text = compile_text(fresh, briefing)

    print(f"Sending digest to {settings.DIGEST_RECIPIENTS}...")
    send_digest(subject, html, text)
    mark_sent(fresh)
    print("Sent.")

    print("Publishing to site/data...")
    publish(fresh, briefing, run=run_label)
    print("Done.")

    return fresh


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
