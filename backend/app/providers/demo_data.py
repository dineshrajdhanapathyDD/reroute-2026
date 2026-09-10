"""Deterministic demo data for Re:Route AI.

All data here is clearly labelled DEMO. It is realistic but simulated — nothing
claims real-time availability. This module is the ONLY place demo data lives;
the agent and engine never hard-code availability.
"""
from __future__ import annotations

from datetime import datetime

from app.models import (
    DataConfidence,
    Flight,
    Hotel,
    Priority,
    Session,
    SessionStatus,
)

# re:Invent 2026 runs Mon Nov 30 – Fri Dec 4.
EVENT_YEAR = 2026


def _dt(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(EVENT_YEAR, month, day, hour, minute)


# --------------------------------------------------------------------------- #
# Flights  (Chennai MAA -> Las Vegas LAS, arriving before the event)
# --------------------------------------------------------------------------- #
DEMO_FLIGHTS: list[Flight] = [
    Flight(
        id="fl-1",
        airline="Emirates",
        origin="Chennai (MAA)",
        destination="Las Vegas (LAS)",
        depart=_dt(11, 28, 4, 30),
        arrive=_dt(11, 29, 16, 30),  # arrives Sunday afternoon (1 day early)
        duration_minutes=24 * 60 + 30,
        stops=1,
        price_usd=1180,
        confidence=DataConfidence.DEMO,
    ),
    Flight(
        id="fl-2",
        airline="Qatar Airways",
        origin="Chennai (MAA)",
        destination="Las Vegas (LAS)",
        depart=_dt(11, 28, 3, 10),
        arrive=_dt(11, 29, 22, 15),  # arrives Sunday late evening
        duration_minutes=27 * 60 + 5,
        stops=1,
        price_usd=1090,
        confidence=DataConfidence.DEMO,
    ),
    Flight(
        id="fl-3",
        airline="Etihad",
        origin="Chennai (MAA)",
        destination="Las Vegas (LAS)",
        depart=_dt(11, 29, 6, 0),
        arrive=_dt(11, 30, 9, 40),  # arrives Monday morning — risky, same day
        duration_minutes=29 * 60 + 40,
        stops=2,
        price_usd=940,
        confidence=DataConfidence.DEMO,
    ),
    Flight(
        id="fl-4",
        airline="Singapore Airlines",
        origin="Chennai (MAA)",
        destination="Las Vegas (LAS)",
        depart=_dt(11, 28, 23, 55),
        arrive=_dt(11, 29, 19, 5),  # arrives Sunday evening
        duration_minutes=26 * 60 + 10,
        stops=1,
        price_usd=1320,
        confidence=DataConfidence.DEMO,
    ),
]


# --------------------------------------------------------------------------- #
# Hotels  (distance to the "main venue" — the Venetian)
# --------------------------------------------------------------------------- #
DEMO_HOTELS: list[Hotel] = [
    Hotel(
        id="ho-1",
        name="The Venetian Resort",
        price_per_night_usd=239,
        distance_to_main_venue_km=0.1,
        walk_minutes_to_main_venue=2,
        rating=4.6,
        confidence=DataConfidence.DEMO,
    ),
    Hotel(
        id="ho-2",
        name="Wynn Las Vegas",
        price_per_night_usd=210,
        distance_to_main_venue_km=0.6,
        walk_minutes_to_main_venue=8,
        rating=4.7,
        confidence=DataConfidence.DEMO,
    ),
    Hotel(
        id="ho-3",
        name="Harrah's Las Vegas",
        price_per_night_usd=149,
        distance_to_main_venue_km=1.1,
        walk_minutes_to_main_venue=15,
        rating=4.1,
        confidence=DataConfidence.DEMO,
    ),
    Hotel(
        id="ho-4",
        name="The Mirage Area Inn",
        price_per_night_usd=119,
        distance_to_main_venue_km=1.9,
        walk_minutes_to_main_venue=26,
        rating=3.9,
        confidence=DataConfidence.DEMO,
    ),
]


# --------------------------------------------------------------------------- #
# Sessions  (topic-tagged, spread across venues/days)
# --------------------------------------------------------------------------- #
DEMO_SESSIONS: list[Session] = [
    Session(
        id="se-1",
        title="Building production-ready AI agents on AWS",
        topic="Agents",
        format="Breakout",
        venue="Venetian",
        room="L3",
        day="Tuesday",
        start=_dt(12, 1, 9, 0),
        end=_dt(12, 1, 10, 0),
        priority=Priority.MUST,
        status=SessionStatus.AVAILABLE,
        match_score=97,
    ),
    Session(
        id="se-2",
        title="Amazon Bedrock: orchestrating multi-agent systems",
        topic="Amazon Bedrock",
        format="Breakout",
        venue="Caesars Forum",
        room="Forum 120",
        day="Tuesday",
        start=_dt(12, 1, 10, 30),
        end=_dt(12, 1, 11, 30),
        priority=Priority.HIGH,
        status=SessionStatus.AVAILABLE,
        match_score=93,
    ),
    Session(
        id="se-3",
        title="Generative AI hands-on: build an agent workflow",
        topic="Generative AI",
        format="Workshop",
        venue="MGM Grand",
        room="Premier 314",
        day="Tuesday",
        start=_dt(12, 1, 13, 0),
        end=_dt(12, 1, 15, 0),
        priority=Priority.HIGH,
        status=SessionStatus.AVAILABLE,
        match_score=90,
    ),
    # Deliberate conflict with se-2 (overlaps + different venue)
    Session(
        id="se-4",
        title="Serverless patterns for agentic apps",
        topic="Serverless",
        format="Chalk Talk",
        venue="MGM Grand",
        room="Boulevard 155",
        day="Tuesday",
        start=_dt(12, 1, 11, 0),
        end=_dt(12, 1, 12, 0),
        priority=Priority.MEDIUM,
        status=SessionStatus.AVAILABLE,
        match_score=71,
    ),
    Session(
        id="se-5",
        title="Evaluating and observing LLM agents in production",
        topic="Agents",
        format="Breakout",
        venue="Venetian",
        room="L2",
        day="Wednesday",
        start=_dt(12, 2, 9, 30),
        end=_dt(12, 2, 10, 30),
        priority=Priority.HIGH,
        status=SessionStatus.AVAILABLE,
        match_score=88,
    ),
    Session(
        id="se-6",
        title="Amazon Bedrock AgentCore deep dive",
        topic="Amazon Bedrock",
        format="Breakout",
        venue="Wynn",
        room="Latour 5",
        day="Wednesday",
        start=_dt(12, 2, 11, 0),
        end=_dt(12, 2, 12, 0),
        priority=Priority.MEDIUM,
        status=SessionStatus.AVAILABLE,
        match_score=85,
    ),
    Session(
        id="se-7",
        title="Securing generative AI applications",
        topic="Security",
        format="Breakout",
        venue="Caesars Forum",
        room="Forum 106",
        day="Wednesday",
        start=_dt(12, 2, 13, 30),
        end=_dt(12, 2, 14, 30),
        priority=Priority.LOW,
        status=SessionStatus.AVAILABLE,
        match_score=64,
    ),
    # Alternatives that Recovery Navigator can surface for se-1
    Session(
        id="se-8",
        title="Production-ready AI agents (repeat session)",
        topic="Agents",
        format="Breakout",
        venue="Venetian",
        room="L4",
        day="Tuesday",
        start=_dt(12, 1, 15, 30),
        end=_dt(12, 1, 16, 30),
        priority=Priority.HIGH,
        status=SessionStatus.AVAILABLE,
        match_score=96,
    ),
    Session(
        id="se-9",
        title="Workshop: ship an agent to production with Bedrock",
        topic="Agents",
        format="Workshop",
        venue="Venetian",
        room="L1",
        day="Tuesday",
        start=_dt(12, 1, 16, 0),
        end=_dt(12, 1, 18, 0),
        priority=Priority.MEDIUM,
        status=SessionStatus.AVAILABLE,
        match_score=91,
    ),
]


# --------------------------------------------------------------------------- #
# Venue geography  — (from, to) -> (distance_km, walk_minutes, shuttle)
# Symmetric; also used for hotel->venue via "Hotel".
# --------------------------------------------------------------------------- #
_VENUE_MATRIX: dict[frozenset[str], tuple[float, int, bool]] = {
    frozenset({"Venetian", "Caesars Forum"}): (1.3, 16, True),
    frozenset({"Venetian", "MGM Grand"}): (4.2, 45, True),
    frozenset({"Venetian", "Wynn"}): (0.7, 9, False),
    frozenset({"Caesars Forum", "MGM Grand"}): (3.1, 38, True),
    frozenset({"Caesars Forum", "Wynn"}): (1.6, 19, True),
    frozenset({"MGM Grand", "Wynn"}): (4.6, 50, True),
    frozenset({"Hotel", "Venetian"}): (0.1, 2, False),
    frozenset({"Hotel", "Caesars Forum"}): (1.3, 16, True),
    frozenset({"Hotel", "MGM Grand"}): (4.2, 45, True),
    frozenset({"Hotel", "Wynn"}): (0.7, 9, False),
}


def venue_travel(from_venue: str, to_venue: str) -> tuple[float, int, bool]:
    if from_venue == to_venue:
        return (0.0, 0, False)
    key = frozenset({from_venue, to_venue})
    return _VENUE_MATRIX.get(key, (2.0, 25, False))  # sensible fallback estimate
