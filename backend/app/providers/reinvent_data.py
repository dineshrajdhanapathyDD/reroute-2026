"""Real AWS re:Invent 2026 structural data (public, factual reference).

Event dates, the six venues, campus-shuttle/walk relationships, keynotes, Expo
zones, and the Thursday security focus. Used by Wayfinder (travel), the
Navigator (opportunities), and the UI. Not scraped — encoded from public event
information, with official links kept in official_links.py.
"""
from __future__ import annotations

from app.official_links import OFFICIAL_LINKS

EVENT = {
    "id": "reinvent-2026",
    "name": "AWS re:Invent 2026",
    "startDate": "2026-11-30",
    "endDate": "2026-12-04",
    "kickoffDate": "2026-11-29",  # Sunday badge pickup + kickoff
    "timezone": "America/Los_Angeles",
    "city": "Las Vegas",
    "sessionCount": "2,200+",
    "speakerCount": "3,000+",
    "interactivePercentage": 70,
    "launchSessions": "150+",
    "official_url": OFFICIAL_LINKS["reinventHome"],
}

# Six venues. type: conference_venue | conference_hotel (has programming) etc.
VENUES = [
    {"name": "Caesars Forum", "type": "conference_venue", "programming": True,
     "nearbyHotels": ["Caesars Palace", "Harrah's", "Flamingo"], "accessibility": "Full step-free access"},
    {"name": "Caesars Palace", "type": "conference_hotel", "programming": True,
     "nearbyHotels": ["Caesars Palace"], "accessibility": "Full step-free access"},
    {"name": "Encore", "type": "conference_hotel", "programming": True,
     "nearbyHotels": ["Encore", "Wynn"], "accessibility": "Full step-free access"},
    {"name": "MGM Grand", "type": "conference_hotel", "programming": True,
     "nearbyHotels": ["MGM Grand", "Signature"], "accessibility": "Full step-free access"},
    {"name": "The Venetian", "type": "conference_hotel", "programming": True,
     "nearbyHotels": ["The Venetian", "Palazzo"], "accessibility": "Full step-free access"},
    {"name": "Wynn", "type": "conference_hotel", "programming": True,
     "nearbyHotels": ["Wynn", "Encore"], "accessibility": "Full step-free access"},
]

# Travel between venues: (dist_km, walk_min, shuttle_min|None, walkable)
# The Strip is long; MGM (south) to Venetian/Wynn/Encore (north) is shuttle-only.
VENUE_TRAVEL: dict[frozenset, dict] = {
    frozenset({"The Venetian", "Wynn"}): {"km": 0.7, "walk": 9, "shuttle": None, "walkable": True},
    frozenset({"The Venetian", "Encore"}): {"km": 0.8, "walk": 11, "shuttle": None, "walkable": True},
    frozenset({"Wynn", "Encore"}): {"km": 0.2, "walk": 3, "shuttle": None, "walkable": True},
    frozenset({"The Venetian", "Caesars Forum"}): {"km": 1.3, "walk": 17, "shuttle": 15, "walkable": False},
    frozenset({"The Venetian", "Caesars Palace"}): {"km": 1.4, "walk": 18, "shuttle": 15, "walkable": False},
    frozenset({"Caesars Forum", "Caesars Palace"}): {"km": 0.3, "walk": 5, "shuttle": None, "walkable": True},
    frozenset({"Wynn", "Caesars Forum"}): {"km": 1.6, "walk": 21, "shuttle": 18, "walkable": False},
    frozenset({"Caesars Forum", "MGM Grand"}): {"km": 5.0, "walk": 60, "shuttle": 25, "walkable": False},
    frozenset({"The Venetian", "MGM Grand"}): {"km": 5.5, "walk": 65, "shuttle": 28, "walkable": False},
    frozenset({"Wynn", "MGM Grand"}): {"km": 6.0, "walk": 70, "shuttle": 30, "walkable": False},
    frozenset({"Encore", "MGM Grand"}): {"km": 6.1, "walk": 71, "shuttle": 30, "walkable": False},
    frozenset({"Caesars Palace", "MGM Grand"}): {"km": 4.6, "walk": 55, "shuttle": 24, "walkable": False},
    frozenset({"Encore", "Caesars Forum"}): {"km": 1.7, "walk": 22, "shuttle": 18, "walkable": False},
    frozenset({"Encore", "Caesars Palace"}): {"km": 1.8, "walk": 23, "shuttle": 18, "walkable": False},
    frozenset({"Wynn", "Caesars Palace"}): {"km": 1.7, "walk": 22, "shuttle": 18, "walkable": False},
}


_VENUE_ALIASES = {
    "venetian": "The Venetian",
    "the venetian": "The Venetian",
    "wynn": "Wynn",
    "encore": "Encore",
    "mgm grand": "MGM Grand",
    "mgm": "MGM Grand",
    "caesars forum": "Caesars Forum",
    "caesars palace": "Caesars Palace",
}


def normalize_venue(name: str) -> str:
    return _VENUE_ALIASES.get((name or "").strip().lower(), name)


def venue_travel(a: str, b: str) -> dict:
    a, b = normalize_venue(a), normalize_venue(b)
    if a == b:
        return {"km": 0.0, "walk": 0, "shuttle": None, "walkable": True}
    return VENUE_TRAVEL.get(frozenset({a, b}), {"km": 3.0, "walk": 38, "shuttle": 20, "walkable": False})


KEYNOTES = [
    {"id": "kn-1", "title": "CEO Keynote", "speaker": "Matt Garman", "day": "Tuesday",
     "time": "2026-12-01T08:00:00", "venue": "The Venetian", "virtual": True,
     "topics": ["Agents", "Generative AI", "Amazon Bedrock"],
     "official_url": OFFICIAL_LINKS["keynotes"]},
    {"id": "kn-2", "title": "Dr. Werner Vogels Keynote", "speaker": "Werner Vogels", "day": "Thursday",
     "time": "2026-12-03T08:30:00", "venue": "The Venetian", "virtual": True,
     "topics": ["Architecture", "Serverless"], "official_url": OFFICIAL_LINKS["keynotes"]},
]

EXPO_ACTIVITIES = [
    {"id": "ex-1", "type": "expert_meeting", "zone": "AWS Village", "topic": "Agents",
     "title": "Agentic AI experts — AWS Village", "duration_min": 30, "learning_value": "high",
     "official_url": OFFICIAL_LINKS["expo"]},
    {"id": "ex-2", "type": "lightning_theater", "zone": "Lightning Theaters", "topic": "Generative AI",
     "title": "GenAI in production — Lightning Theater", "duration_min": 20, "learning_value": "medium",
     "official_url": OFFICIAL_LINKS["expo"]},
    {"id": "ex-3", "type": "expert_meeting", "zone": "Builder Community Zone", "topic": "Amazon Bedrock",
     "title": "Bedrock AgentCore Q&A — Builder Community", "duration_min": 30, "learning_value": "high",
     "official_url": OFFICIAL_LINKS["expo"]},
    {"id": "ex-4", "type": "expert_meeting", "zone": "Partner Advantage Zone", "topic": "Security",
     "title": "Securing GenAI — Partner Advantage", "duration_min": 30, "learning_value": "medium",
     "official_url": OFFICIAL_LINKS["sponsors"]},
]

SECURITY_FOCUS = {
    "venue": "Wynn",
    "day": "Thursday",
    "date": "2026-12-03",
    "sessions": "70+",
    "interactiveSessions": 44,
    "levels": "300-500",
    "official_url": OFFICIAL_LINKS["securityFocus"],
}

EXPERIENCES = [
    {"id": "exp-1", "title": "re:Play", "day": "Thursday", "type": "celebration",
     "official_url": OFFICIAL_LINKS["uniquelyReinvent"]},
    {"id": "exp-2", "title": "Expo Welcome Reception", "day": "Monday", "type": "networking",
     "official_url": OFFICIAL_LINKS["expo"]},
    {"id": "exp-3", "title": "/dev/quest", "day": "Wednesday", "type": "gamified",
     "official_url": OFFICIAL_LINKS["uniquelyReinvent"]},
    {"id": "exp-4", "title": "Game Night", "day": "Tuesday", "type": "community",
     "official_url": OFFICIAL_LINKS["uniquelyReinvent"]},
]
