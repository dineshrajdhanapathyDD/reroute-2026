"""Session enrichment shared by demo and catalog providers.

Fills derived fields (learning_mode, hands_on, catalog_url) from the session
format, and normalizes level. Keeps a single place so demo and imported data
behave identically.
"""
from __future__ import annotations

from app.models import Session, format_meta
from app.official_links import session_catalog_url

# Normalize catalog format strings to our canonical SESSION_FORMATS keys.
_FORMAT_ALIASES = {
    "breakout session": "Breakout",
    "breakout": "Breakout",
    "chalk talk": "Chalk Talk",
    "code talk": "Code Talk",
    "builders' session": "Builders' Session",
    "builders session": "Builders' Session",
    "workshop": "Workshop",
    "lab": "Lab",
    "gamified learning": "Gamified Learning",
    "lightning talk": "Lightning Talk",
    "exam prep": "Exam Prep",
    "bootcamp": "Bootcamp",
    "keynote": "Keynote",
}


def normalize_format(fmt: str) -> str:
    return _FORMAT_ALIASES.get((fmt or "").strip().lower(), fmt or "Breakout")


def enrich_session(s: Session) -> Session:
    s.format = normalize_format(s.format)
    meta = format_meta(s.format)
    if not s.learning_mode or s.learning_mode == "Watch and Learn":
        s.learning_mode = meta["mode"]
    s.hands_on = meta["hands_on"]
    if not s.catalog_url:
        s.catalog_url = s.official_url or session_catalog_url(s.id)
    if not s.level:
        s.level = "300"
    return s


def enrich_all(sessions: list[Session]) -> list[Session]:
    return [enrich_session(s) for s in sessions]
