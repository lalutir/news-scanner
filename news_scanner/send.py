"""Sends the compiled digest via Mailgun's HTTP API directly - not through
Mailcow's SMTP submission port. See CLAUDE.md's Infrastructure section."""

import requests

from news_scanner import settings  # noqa: F401 - loads .env as a side effect


def send_digest(subject, html, text, recipients=None, from_email=None,
                 domain=None, api_key=None):
    recipients = recipients if recipients is not None else settings.DIGEST_RECIPIENTS
    from_email = from_email or settings.DIGEST_FROM_EMAIL
    domain = domain or settings.MAILGUN_DOMAIN
    api_key = api_key or settings.MAILGUN_API_KEY

    if not recipients:
        raise ValueError("No DIGEST_RECIPIENTS configured")
    if not (from_email and domain and api_key):
        raise ValueError("Mailgun is not fully configured - check .env")

    response = requests.post(
        f"https://api.mailgun.net/v3/{domain}/messages",
        auth=("api", api_key),
        data={
            "from": from_email,
            "to": recipients,
            "subject": subject,
            "text": text,
            "html": html,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
