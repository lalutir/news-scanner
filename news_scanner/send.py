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
        # mg.lalutir.com is an EU-region Mailgun domain - the US endpoint
        # (api.mailgun.net) rejects an EU key with a bare 401 Forbidden.
        f"https://api.eu.mailgun.net/v3/{domain}/messages",
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
    if not response.ok:
        # Mailgun's response body names the actual reason (bad key, wrong
        # region, unverified domain, ...) - raise_for_status() alone hides it.
        raise RuntimeError(
            f"Mailgun request failed ({response.status_code}): {response.text}"
        )
    return response.json()
