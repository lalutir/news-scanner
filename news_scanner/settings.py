"""Loads .env once and exposes the settings every stage needs."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")
DIGEST_FROM_EMAIL = os.environ.get("DIGEST_FROM_EMAIL")
DIGEST_RECIPIENTS = [
    addr.strip()
    for addr in os.environ.get("DIGEST_RECIPIENTS", "").split(",")
    if addr.strip()
]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Clustering needs to judge "same specific event" vs. "same broad subject"
# across languages and sources - one call per run, so quality matters more
# than the per-item cost that rules out Sonnet for the filter stage.
CLUSTER_MODEL = "claude-sonnet-5"
