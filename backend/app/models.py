"""Pydantic data models for Re:Route AI.

These define the *structured* shape the backend returns so the frontend can
render cards, timelines, maps and checklists — never just plain text.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums / shared vocabulary
# --------------------------------------------------------------------------- #
class DataConfidence(str, Enum):
    """How trustworthy a piece of data is. Surfaced in the UI as a badge."""

    LIVE = "live"
    VERIFIED = "verified"
    ESTIMATED = "estimated"
    DEMO = "demo"
    UNAVAILABLE = "unavailable"


class Priority(str, Enum):
    MUST = "must"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CapacityState(str, Enum):
    SUSTAINABLE = "sustainable"  # green
    BUSY = "busy"  # yellow
    OVERLOADED = "overloaded"  # red


class SessionStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    LIMITED = "limited"
    FULL = "full"
    STANDBY = "standby"
    CANCELLED = "cancelled"
    REPEAT_AVAILABLE = "repeat_available"
    RECORDING_AVAILABLE = "recording_available"


# Session formats and their typical durations (minutes) + learning mode.
SESSION_FORMATS: dict[str, dict] = {
    "Keynote": {"duration": 120, "mode": "Watch and Learn", "hands_on": False},
    "Breakout": {"duration": 60, "mode": "Watch and Learn", "hands_on": False},
    "Lightning Talk": {"duration": 20, "mode": "Watch and Learn", "hands_on": False},
    "Chalk Talk": {"duration": 60, "mode": "Work Alongside Experts", "hands_on": True},
    "Code Talk": {"duration": 60, "mode": "Work Alongside Experts", "hands_on": True},
    "Builders' Session": {"duration": 60, "mode": "Work Alongside Experts", "hands_on": True},
    "Workshop": {"duration": 120, "mode": "Build It Yourself", "hands_on": True},
    "Lab": {"duration": 90, "mode": "Build It Yourself", "hands_on": True},
    "Gamified Learning": {"duration": 120, "mode": "Build It Yourself", "hands_on": True},
    "Exam Prep": {"duration": 90, "mode": "Certification", "hands_on": False},
    "Bootcamp": {"duration": 360, "mode": "Certification", "hands_on": True},
}

LEARNING_MODES = ["Watch and Learn", "Work Alongside Experts", "Build It Yourself", "Certification"]


def format_meta(fmt: str) -> dict:
    return SESSION_FORMATS.get(fmt, {"duration": 60, "mode": "Watch and Learn", "hands_on": False})


# --------------------------------------------------------------------------- #
# Trip preferences (input)
# --------------------------------------------------------------------------- #
class TripPreferences(BaseModel):
    origin: str = "Chennai"
    destination: str = "Las Vegas"
    arrive_days_early: int = 1
    travelers: int = 1
    preferred_flight_time: Optional[str] = None  # "morning" | "evening" | None
    hotel_budget_per_night: Optional[float] = None
    preferred_hotel_area: Optional[str] = None  # e.g. "near venues"
    learning_goal: str = "Generative AI and AI Agents"
    topics: list[str] = Field(default_factory=list)
    event_start: date = date(2026, 11, 30)  # re:Invent 2026 (Mon)
    event_end: date = date(2026, 12, 4)
    max_daily_walking_km: float = 7.0


# --------------------------------------------------------------------------- #
# Flights
# --------------------------------------------------------------------------- #
class Flight(BaseModel):
    id: str
    airline: str
    origin: str
    destination: str
    depart: datetime
    arrive: datetime
    duration_minutes: int
    stops: int
    price_usd: float
    confidence: DataConfidence = DataConfidence.DEMO


class FlightRecommendation(BaseModel):
    flight: Flight
    recommended: bool = False
    reason: str = ""


# --------------------------------------------------------------------------- #
# Hotels
# --------------------------------------------------------------------------- #
class Hotel(BaseModel):
    id: str
    name: str
    price_per_night_usd: float
    distance_to_main_venue_km: float
    walk_minutes_to_main_venue: int
    rating: float
    confidence: DataConfidence = DataConfidence.DEMO


class HotelRecommendation(BaseModel):
    hotel: Hotel
    recommended: bool = False
    reason: str = ""


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
class Session(BaseModel):
    id: str
    title: str
    topic: str
    format: str  # Breakout | Workshop | Chalk Talk | Code Talk | Lab | ...
    venue: str
    room: str
    day: str  # "Tuesday"
    start: datetime
    end: datetime
    priority: Priority = Priority.MEDIUM
    status: SessionStatus = SessionStatus.AVAILABLE
    match_score: int = 0  # 0-100 relevance to learning goal
    level: str = "300"  # 100-500
    learning_mode: str = "Watch and Learn"  # derived from format
    hands_on: bool = False
    official_url: Optional[str] = None  # per-session official URL when known
    catalog_url: Optional[str] = None  # fallback: official Event Catalog
    why: str = ""  # short agent explanation of why this session was kept
    confidence: DataConfidence = DataConfidence.DEMO


class SessionConflict(BaseModel):
    session_a_id: str
    session_b_id: str
    reason: str  # time overlap | infeasible transition
    recommendation: str
    keep_session_id: str
    drop_session_id: str


# --------------------------------------------------------------------------- #
# Travel / walking between venues
# --------------------------------------------------------------------------- #
class TravelLeg(BaseModel):
    from_venue: str
    to_venue: str
    from_session_id: Optional[str] = None
    to_session_id: Optional[str] = None
    distance_km: float
    walk_minutes: int
    shuttle_available: bool = False
    recommended_depart: Optional[datetime] = None
    arrival: Optional[datetime] = None
    buffer_minutes: int = 0
    confidence: DataConfidence = DataConfidence.ESTIMATED


# --------------------------------------------------------------------------- #
# Daily schedule
# --------------------------------------------------------------------------- #
class ScheduleItem(BaseModel):
    time: str  # "9:00 AM"
    activity: str
    venue: Optional[str] = None
    session_id: Optional[str] = None
    kind: str = "session"  # session | meal | travel | break | arrival | hotel | prep
    icon: str = "📍"


class DaySchedule(BaseModel):
    day: str  # "Tuesday"
    items: list[ScheduleItem] = Field(default_factory=list)
    walking_km: float = 0.0
    venue_changes: int = 0
    break_minutes: int = 0
    networking_minutes: int = 0
    capacity: CapacityState = CapacityState.SUSTAINABLE


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #
class ChecklistItem(BaseModel):
    label: str
    done: bool = False


class ChecklistSection(BaseModel):
    title: str
    items: list[ChecklistItem]


# --------------------------------------------------------------------------- #
# Scores
# --------------------------------------------------------------------------- #
class Scores(BaseModel):
    journey_score: int = 0  # overall trip readiness/progress 0-100
    route_quality: int = 0  # feasibility/quality of today's route 0-100
    learning_coverage: dict[str, int] = Field(default_factory=dict)
    # Multi-factor breakdown (Journey Analyst)
    breakdown: dict[str, int] = Field(default_factory=dict)
    # Learning-mode mix as percentages, e.g. {"Watch and Learn": 40, ...}
    learning_mode_mix: dict[str, int] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Agent activity events (surfaced, never chain-of-thought)
# --------------------------------------------------------------------------- #
class AgentEvent(BaseModel):
    agent: str  # Navigator | Session Scout | Route Planner | Wayfinder | Recovery Navigator
    icon: str
    task: str
    action: str
    result: str
    status: str = "done"  # done | active | waiting


# --------------------------------------------------------------------------- #
# The full structured plan (top-level response)
# --------------------------------------------------------------------------- #
class TripSummary(BaseModel):
    origin: str
    destination: str
    arrival_date: Optional[str] = None
    departure_date: Optional[str] = None
    learning_goal: str
    demo_mode: bool = True


class DroppedSession(BaseModel):
    id: str
    title: str
    reason: str  # why the agent set it aside (conflict / tight transition / day full)


class Plan(BaseModel):
    trip: TripSummary
    flight_recommendations: list[FlightRecommendation] = Field(default_factory=list)
    hotel_recommendations: list[HotelRecommendation] = Field(default_factory=list)
    sessions: list[Session] = Field(default_factory=list)
    dropped_sessions: list[DroppedSession] = Field(default_factory=list)
    daily_schedule: list[DaySchedule] = Field(default_factory=list)
    travel_routes: list[TravelLeg] = Field(default_factory=list)
    conflicts: list[SessionConflict] = Field(default_factory=list)
    preparation_checklist: list[ChecklistSection] = Field(default_factory=list)
    scores: Scores = Field(default_factory=Scores)
    agent_activity: list[AgentEvent] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# ReRoute (recovery) models
# --------------------------------------------------------------------------- #
class RouteChangeMetric(BaseModel):
    label: str
    before: str
    after: str
    direction: str  # up | down | same  (semantic improvement direction)


class Alternative(BaseModel):
    session: Session
    match_score: int
    note: str


class RerouteResult(BaseModel):
    reason: str
    dropped_session_id: str
    alternatives: list[Alternative] = Field(default_factory=list)
    recommended_alternative_id: Optional[str] = None
    metrics: list[RouteChangeMetric] = Field(default_factory=list)
    agent_activity: list[AgentEvent] = Field(default_factory=list)
