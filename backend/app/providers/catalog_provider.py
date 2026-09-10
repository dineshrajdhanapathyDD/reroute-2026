"""Real re:Invent session catalog provider.

The official catalog at
https://registration.awsevents.com/.../eventcatalog is a Cvent-hosted
single-page app whose sessions load *after login* from a private, authenticated
API. It cannot be scraped anonymously and there is no public, stable endpoint,
so runtime scraping would be brittle and is out of scope for a demo.

Instead, this provider loads a catalog you export once to a local file and maps
it into our `Session` model. It implements the exact same `SessionProvider`
interface as the demo provider, so the agent, tools and UI are unchanged — only
the data source differs.

Supported input formats (auto-detected by extension):
  * .json — a list of session objects, or an object with a "sessions"/"data"
            list. Field names are matched flexibly (see FIELD_ALIASES).
  * .csv  — one session per row; header names matched via FIELD_ALIASES.

Point the app at a file with the REROUTE_SESSION_CATALOG environment variable:

    $env:REROUTE_SESSION_CATALOG = "d:\\path\\to\\reinvent2026_sessions.json"

If the variable is unset or the file is missing/invalid, we transparently fall
back to the deterministic demo catalog so the app always runs.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from app.models import DataConfidence, Priority, Session, SessionStatus
from app.providers.base import SessionProvider
from app.providers.demo_providers import DemoSessionProvider

# Map many possible source column names -> our canonical field.
FIELD_ALIASES: dict[str, list[str]] = {
    "id": ["id", "sessionId", "code", "sessionCode", "session_code", "abbreviation"],
    "title": ["title", "name", "sessionTitle", "session_name"],
    "topic": ["topic", "track", "primaryTopic", "primary_topic", "category", "theme"],
    "format": ["format", "sessionType", "session_type", "type"],
    "venue": ["venue", "location", "building", "room_building"],
    "room": ["room", "roomName", "room_name", "location_detail"],
    "day": ["day", "dayOfWeek", "weekday"],
    "start": ["start", "startTime", "start_time", "startDateTime", "startsAt"],
    "end": ["end", "endTime", "end_time", "endDateTime", "endsAt"],
    "level": ["level", "sessionLevel", "difficulty"],
    "description": ["description", "abstract", "summary"],
}

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Topic keywords used to derive a normalized topic + learning match score when
# the source topic is missing or free-text.
_TOPIC_KEYWORDS = {
    "Agents": ["agent", "agentic", "agentcore"],
    "Generative AI": ["generative ai", "gen ai", "genai", "llm", "foundation model"],
    "Amazon Bedrock": ["bedrock"],
    "Amazon SageMaker": ["sagemaker"],
    "Serverless": ["serverless", "lambda"],
    "Containers": ["container", "eks", "ecs", "kubernetes", "fargate"],
    "Data": ["data", "analytics", "database", "redshift", "aurora"],
    "Security": ["security", "iam", "encryption"],
    "Networking": ["network", "vpc"],
    "Architecture": ["architecture", "well-architected"],
}


def _first(d: dict, keys: list[str]):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
        # case-insensitive fallback
        for actual in d:
            if actual.lower() == k.lower() and d[actual] not in (None, ""):
                return d[actual]
    return None


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # ISO with timezone
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _derive_topic(title: str, raw_topic: str | None) -> str:
    text = f"{raw_topic or ''} {title}".lower()
    for topic, kws in _TOPIC_KEYWORDS.items():
        if any(k in text for k in kws):
            return topic
    return (raw_topic or "General").strip() or "General"


def _match_score(topic: str, title: str) -> int:
    # Higher for the core "learning journey" topics this product targets.
    boost = {"Agents": 95, "Generative AI": 90, "Amazon Bedrock": 88}
    return boost.get(topic, 70)


def _priority_from_level(level) -> Priority:
    s = str(level or "").lower()
    if any(x in s for x in ("400", "expert", "advanced")):
        return Priority.HIGH
    if any(x in s for x in ("300",)):
        return Priority.MEDIUM
    return Priority.MEDIUM


def _row_to_session(row: dict, index: int) -> Session | None:
    title = _first(row, FIELD_ALIASES["title"])
    if not title:
        return None
    start = _parse_dt(_first(row, FIELD_ALIASES["start"]))
    end = _parse_dt(_first(row, FIELD_ALIASES["end"]))
    if start and not end:
        # assume a 60-minute session if end is missing
        from datetime import timedelta
        end = start + timedelta(minutes=60)
    if not start or not end:
        return None

    day = _first(row, FIELD_ALIASES["day"]) or _WEEKDAYS[start.weekday()]
    raw_topic = _first(row, FIELD_ALIASES["topic"])
    topic = _derive_topic(title, raw_topic)
    sid = str(_first(row, FIELD_ALIASES["id"]) or f"cat-{index}")

    return Session(
        id=sid,
        title=str(title),
        topic=topic,
        format=str(_first(row, FIELD_ALIASES["format"]) or "Breakout"),
        venue=str(_first(row, FIELD_ALIASES["venue"]) or "TBD"),
        room=str(_first(row, FIELD_ALIASES["room"]) or ""),
        day=str(day),
        start=start,
        end=end,
        priority=_priority_from_level(_first(row, FIELD_ALIASES["level"])),
        status=SessionStatus.AVAILABLE,
        match_score=_match_score(topic, str(title)),
        level=_normalize_level(_first(row, FIELD_ALIASES["level"])),
        official_url=_first(row, ["officialUrl", "official_url", "url", "catalogUrl", "link"]),
        confidence=DataConfidence.VERIFIED,  # from the real exported catalog
    )


def _normalize_level(value) -> str:
    m = re.search(r"(100|200|300|400|500)", str(value or ""))
    return m.group(1) if m else "300"


def _rows_to_sessions(rows: list[dict]) -> list[Session]:
    from app.providers.enrich import enrich_session

    sessions: list[Session] = []
    for i, row in enumerate(rows):
        s = _row_to_session(row, i)
        if s:
            sessions.append(enrich_session(s))
    return sessions


def load_catalog_from_text(text: str, fmt: str = "json") -> list[Session]:
    """Parse catalog content from a pasted string (JSON or CSV)."""
    text = (text or "").strip()
    if not text:
        return []
    fmt = (fmt or "json").lower()
    if fmt == "csv":
        rows = list(csv.DictReader(io.StringIO(text)))
    else:
        data = json.loads(text)
        if isinstance(data, dict):
            rows = data.get("sessions") or data.get("data") or data.get("items") or []
        else:
            rows = data
    return _rows_to_sessions(rows)


def load_catalog(path: str | os.PathLike) -> list[Session]:
    """Load and normalize sessions from a JSON or CSV export file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    if p.suffix.lower() == ".json":
        return load_catalog_from_text(p.read_text(encoding="utf-8"), "json")
    elif p.suffix.lower() == ".csv":
        return load_catalog_from_text(p.read_text(encoding="utf-8"), "csv")
    raise ValueError(f"Unsupported catalog format: {p.suffix}")


class CatalogSessionProvider(SessionProvider):
    """SessionProvider backed by an exported catalog file, with demo fallback."""

    # Bundled real re:Invent 2026 catalog (scraped from the official API).
    _BUNDLED = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reinvent2026_sessions.json")

    def __init__(self, path: str | None = None):
        env_path = os.getenv("REROUTE_SESSION_CATALOG")
        default = self._BUNDLED if os.path.exists(self._BUNDLED) else None
        self.path = path or env_path or default
        self.source = "demo"
        self._sessions: dict[str, Session] = {}
        self._fallback = DemoSessionProvider()
        self._load()

    def _load(self) -> None:
        if self.path:
            try:
                sessions = load_catalog(self.path)
                if sessions:
                    self._sessions = {s.id: s for s in sessions}
                    self.source = "catalog"
                    return
            except Exception as exc:  # noqa: BLE001 - never break the app on bad data
                print(f"[catalog] failed to load {self.path}: {exc}; using demo data")
        self.source = "demo"

    def load_sessions(self, sessions: list[Session]) -> int:
        """Replace the active catalog at runtime (used by paste/upload import)."""
        self._sessions = {s.id: s for s in sessions}
        self.source = "catalog" if sessions else "demo"
        return len(self._sessions)

    # --- SessionProvider interface (mirrors DemoSessionProvider) --- #
    def search_sessions(self, topics, day=None, venue=None):
        if self.source == "demo":
            return self._fallback.search_sessions(topics, day, venue)
        topics_lower = [t.strip().lower() for t in (topics or []) if t.strip()]
        results = []
        for s in self._sessions.values():
            if topics_lower and not any(
                t in s.topic.lower() or t in s.title.lower() for t in topics_lower
            ):
                continue
            if day and s.day.lower() != day.lower():
                continue
            if venue and s.venue.lower() != venue.lower():
                continue
            results.append(deepcopy(s))
        results.sort(key=lambda s: (s.day, s.start))
        return results

    def get_session(self, session_id):
        if self.source == "demo":
            return self._fallback.get_session(session_id)
        s = self._sessions.get(session_id)
        return deepcopy(s) if s else None

    def set_status(self, session_id, status):
        if self.source == "demo":
            return self._fallback.set_status(session_id, status)
        if session_id in self._sessions:
            self._sessions[session_id].status = status
