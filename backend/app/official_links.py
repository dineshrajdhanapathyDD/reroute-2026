"""Official AWS re:Invent links — the single source of truth.

Re:Route AI recommends; AWS re:Invent confirms. Every recommendation that
originates from official information should link back to the authoritative AWS
page. These are the real, current re:Invent 2026 URLs; do not fabricate others.
"""
from __future__ import annotations

OFFICIAL_LINKS: dict[str, str] = {
    "reinventHome": "https://aws.amazon.com/events/reinvent/",
    "registration": "https://registration.awsevents.com/flow/awsevents/reinvent2026/reg",
    "agenda": "https://aws.amazon.com/events/reinvent/agenda/",
    "eventCatalog": "https://registration.awsevents.com/flow/awsevents/reinvent2026/eventcatalog/page/eventcatalog",
    "pricing": "https://aws.amazon.com/events/reinvent/pricing/",
    "approvalToolkit": "https://aws.amazon.com/events/reinvent/approval-toolkit/",
    "accessibility": "https://aws.amazon.com/events/reinvent/plan/accessibility-services/",
    "curatedAgendas": "https://aws.amazon.com/events/reinvent/sessions/curated-agendas/",
    "keynotes": "https://aws.amazon.com/events/reinvent/sessions/keynotes/",
    "howYoullLearn": "https://aws.amazon.com/events/reinvent/sessions/how-youll-learn/",
    "securityFocus": "https://aws.amazon.com/events/reinvent/sessions/security-focus/",
    "expo": "https://aws.amazon.com/events/reinvent/experiences/expo/",
    "uniquelyReinvent": "https://aws.amazon.com/events/reinvent/experiences/uniquely-reinvent/",
    "sponsors": "https://registration.awsevents.com/flow/awsevents/reinvent2026/sponsorcatalog/page/sponsors",
    "login": "https://registration.awsevents.com/flow/awsevents/reinvent2026/login",
}

# The official Event Catalog is the fallback deep link for any session that has
# no specific official URL of its own.
EVENT_CATALOG_URL = OFFICIAL_LINKS["eventCatalog"]


def session_catalog_url(session_id: str | None = None) -> str:
    """Best-effort official deep link for a session.

    The Cvent catalog uses opaque, login-gated per-session URLs we cannot
    fabricate, so we link to the official Event Catalog (source of truth) rather
    than inventing a URL. If a real per-session `officialUrl` is known (e.g. from
    an import), the caller should use that instead.
    """
    return EVENT_CATALOG_URL
