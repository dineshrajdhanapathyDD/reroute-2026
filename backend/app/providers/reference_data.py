"""Static re:Invent reference data — session types and content levels.

The "Session types & levels" page on the catalog is a JS shell, but the content
itself is well-known, stable AWS reference information (what a Breakout vs.
Workshop is; what levels 100-400 mean). Encoding it directly avoids scraping and
lets the agent explain formats and prioritize sessions sensibly.

If AWS changes wording, update this file — it is the single source of truth for
type/level semantics used by the planner and the "explain" tool.
"""
from __future__ import annotations

SESSION_TYPES: list[dict] = [
    {
        "type": "Keynote",
        "duration_min": 120,
        "hands_on": False,
        "description": "Flagship announcements and vision from AWS leaders.",
    },
    {
        "type": "Breakout",
        "duration_min": 60,
        "hands_on": False,
        "description": "Lecture-style session on a specific topic; no reservation needed for most.",
    },
    {
        "type": "Workshop",
        "duration_min": 120,
        "hands_on": True,
        "description": "Hands-on, laptop-required lab. Small capacity; reserve early.",
    },
    {
        "type": "Chalk Talk",
        "duration_min": 60,
        "hands_on": True,
        "description": "Whiteboard-driven, highly interactive Q&A with AWS experts. Small room.",
    },
    {
        "type": "Code Talk",
        "duration_min": 60,
        "hands_on": True,
        "description": "Live coding walkthrough; the presenter builds in front of you.",
    },
    {
        "type": "Builders' Session",
        "duration_min": 60,
        "hands_on": True,
        "description": "Small-group, guided hands-on session (roughly one table per builder).",
    },
    {
        "type": "Lightning Talk",
        "duration_min": 20,
        "hands_on": False,
        "description": "Short, focused talk (often at the Expo).",
    },
]

CONTENT_LEVELS: list[dict] = [
    {"level": "100", "name": "Introductory", "description": "Overview; assumes no prior knowledge."},
    {"level": "200", "name": "Intermediate", "description": "Assumes intro-level familiarity with the topic."},
    {"level": "300", "name": "Advanced", "description": "Deep dive; assumes solid working experience."},
    {"level": "400", "name": "Expert", "description": "Highly technical; for those who build with the service daily."},
]


def session_types() -> list[dict]:
    return list(SESSION_TYPES)


def content_levels() -> list[dict]:
    return list(CONTENT_LEVELS)


def type_duration(session_type: str) -> int:
    for t in SESSION_TYPES:
        if t["type"].lower() == (session_type or "").lower():
            return t["duration_min"]
    return 60


def is_hands_on(session_type: str) -> bool:
    for t in SESSION_TYPES:
        if t["type"].lower() == (session_type or "").lower():
            return t["hands_on"]
    return False
