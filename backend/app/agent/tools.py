"""Agent tools for Re:Route AI.

Each tool is a small, single-responsibility function. They call the planning
engine and providers, and return structured data. They are decorated with the
Strands `@tool` decorator when the SDK is installed, so a real LLM-driven
Strands agent can call them; the deterministic orchestrator calls the same
underlying functions directly, so the demo works with or without the SDK.

Do NOT put orchestration logic here — the agent decides which tools to call.
"""
from __future__ import annotations

from typing import Any

from app.engine import planning
from app.models import Session, SessionStatus, TripPreferences
from app.providers.demo_providers import (
    DemoFlightProvider,
    DemoHotelProvider,
    DemoSessionProvider,
    DemoVenueProvider,
)

# --------------------------------------------------------------------------- #
# Optional Strands decorator. If the SDK isn't installed we use a no-op so the
# same functions remain plain callables for the deterministic orchestrator.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - depends on optional dependency
    from strands import tool as strands_tool

    HAVE_STRANDS = True
except Exception:  # pragma: no cover
    HAVE_STRANDS = False

    def strands_tool(fn=None, **_kwargs):  # type: ignore
        if fn is None:
            return lambda f: f
        return fn


# Shared provider instances. Flights/hotels/venues use demo providers.
# Sessions: when REROUTE_USE_MCP=1, consume the standalone reinvent2026-mcp
# server over MCP; otherwise use the bundled real catalog (or demo). All
# implement the same SessionProvider interface, so nothing downstream changes.
import os as _os

from app.providers.catalog_provider import CatalogSessionProvider


def _make_session_provider():
    if _os.getenv("REROUTE_USE_MCP", "").lower() in ("1", "true", "yes"):
        try:
            from app.providers.mcp_provider import McpSessionProvider

            mcp = McpSessionProvider()
            if mcp.available:
                return mcp
            print(f"[reroute] MCP provider unavailable ({mcp.error}); using bundled catalog")
        except Exception as exc:  # noqa: BLE001
            print(f"[reroute] MCP provider failed ({type(exc).__name__}: {exc}); using bundled catalog")
    return CatalogSessionProvider()  # bundled real catalog, else demo


FLIGHTS = DemoFlightProvider()
HOTELS = DemoHotelProvider()
SESSIONS = _make_session_provider()
VENUES = DemoVenueProvider()


def _prefs_from_dict(d: dict[str, Any] | None) -> TripPreferences:
    return TripPreferences(**(d or {}))


# --------------------------------------------------------------------------- #
# search_flights
# --------------------------------------------------------------------------- #
@strands_tool
def search_flights(preferences: dict | None = None) -> dict:
    """Search available flights for the trip and recommend the best option.

    Compares departure/arrival times, duration, stops and price, and prefers a
    flight that arrives before the attendee's first planned session so they don't
    risk missing an early session after a long-haul flight.
    """
    prefs = _prefs_from_dict(preferences)
    flights = FLIGHTS.search_flights(prefs)
    if not flights:
        return {"error": "no_flights_found", "flight_recommendations": []}
    first_start = min((s.start for s in SESSIONS.search_sessions(prefs.topics)), default=None)
    recs = planning.recommend_flights(flights, prefs, first_start)
    return {"flight_recommendations": [r.model_dump(mode="json") for r in recs]}


# --------------------------------------------------------------------------- #
# search_hotels
# --------------------------------------------------------------------------- #
@strands_tool
def search_hotels(preferences: dict | None = None) -> dict:
    """Search available hotels and recommend one balancing price, rating and
    walking distance to the main re:Invent venue, within budget when provided."""
    prefs = _prefs_from_dict(preferences)
    hotels = HOTELS.search_hotels(prefs)
    if not hotels:
        return {"error": "no_hotels_found", "hotel_recommendations": []}
    recs = planning.recommend_hotels(hotels, prefs)
    return {"hotel_recommendations": [r.model_dump(mode="json") for r in recs]}


# --------------------------------------------------------------------------- #
# search_sessions
# --------------------------------------------------------------------------- #
@strands_tool
def search_sessions(topics: list[str], day: str | None = None, venue: str | None = None) -> dict:
    """Search re:Invent sessions matching the given topics, optionally filtered
    by day and venue. Returns sessions sorted by day and start time."""
    results = SESSIONS.search_sessions(topics, day, venue)
    if not results:
        return {"error": "no_sessions_found", "sessions": []}
    return {"sessions": [s.model_dump(mode="json") for s in results]}


# --------------------------------------------------------------------------- #
# get_session_details
# --------------------------------------------------------------------------- #
@strands_tool
def search_sessions_semantic(query: str, top_k: int = 8) -> dict:
    """Search re:Invent sessions by MEANING, not just keywords, using embeddings.

    Give a natural-language learning goal (e.g. "help me build and ship
    production AI agents") and this ranks sessions by semantic relevance blended
    with topic match. Prefer this over search_sessions when the user describes a
    goal in their own words rather than exact topic names."""
    from app.engine import semantic

    all_sessions = SESSIONS.search_sessions([])  # whole catalog
    ranked = semantic.semantic_search(query, all_sessions, top_k=top_k)
    if not ranked:
        return {"error": "no_sessions_found", "sessions": []}
    return {
        "query": query,
        "provider": semantic.get_index().provider.name,
        "sessions": [s.model_dump(mode="json") for s in ranked],
    }


@strands_tool
def get_session_details(session_id: str) -> dict:
    """Return full details for a single session by id."""
    s = SESSIONS.get_session(session_id)
    if not s:
        return {"error": "session_not_found"}
    return {"session": s.model_dump(mode="json")}


# --------------------------------------------------------------------------- #
# check_session_conflicts
# --------------------------------------------------------------------------- #
@strands_tool
def check_session_conflicts(session_ids: list[str]) -> dict:
    """Detect time overlaps and infeasible venue transitions among the given
    sessions, and recommend which to keep based on priority and match score."""
    sessions = [s for sid in session_ids if (s := SESSIONS.get_session(sid))]
    conflicts = planning.detect_conflicts(sessions, VENUES)
    return {"conflicts": [c.model_dump(mode="json") for c in conflicts]}


# --------------------------------------------------------------------------- #
# estimate_travel_time
# --------------------------------------------------------------------------- #
@strands_tool
def estimate_travel_time(from_venue: str, to_venue: str) -> dict:
    """Estimate travel between two venues: distance (km), walking minutes, and
    whether a shuttle is available. Marked as an estimate, not live data."""
    dist, walk_min, shuttle = planning.estimate_travel_time(from_venue, to_venue, VENUES)
    return {
        "from_venue": from_venue,
        "to_venue": to_venue,
        "distance_km": dist,
        "walk_minutes": walk_min,
        "shuttle_available": shuttle,
        "confidence": "estimated",
    }


# --------------------------------------------------------------------------- #
# build_daily_schedule
# --------------------------------------------------------------------------- #
@strands_tool
def build_daily_schedule(session_ids: list[str], preferences: dict | None = None) -> dict:
    """Build a personalized daily schedule from the selected sessions, including
    meals, breaks, venue transitions, walking totals and human-capacity state."""
    prefs = _prefs_from_dict(preferences)
    sessions = [s for sid in session_ids if (s := SESSIONS.get_session(sid))]
    selected = planning.select_non_conflicting(sessions, VENUES, prefs.topics)
    schedules = planning.build_daily_schedule(selected, VENUES)
    return {
        "selected_session_ids": [s.id for s in selected],
        "daily_schedule": [d.model_dump(mode="json") for d in schedules],
    }


# --------------------------------------------------------------------------- #
# generate_preparation_checklist
# --------------------------------------------------------------------------- #
@strands_tool
def generate_preparation_checklist(has_flight: bool = False, has_hotel: bool = False) -> dict:
    """Generate a personalized preparation checklist (before departure and
    before each event day)."""
    sections = planning.generate_checklist(has_flight, has_hotel)
    return {"preparation_checklist": [s.model_dump(mode="json") for s in sections]}


# --------------------------------------------------------------------------- #
# recommend_alternatives
# --------------------------------------------------------------------------- #
@strands_tool
def recommend_alternatives(dropped_session_id: str) -> dict:
    """Find the best alternative sessions for a session that is full, cancelled
    or missed, protecting the attendee's learning objective (same topic first)."""
    dropped = SESSIONS.get_session(dropped_session_id)
    if not dropped:
        return {"error": "session_not_found", "alternatives": []}
    candidates = SESSIONS.search_sessions([dropped.topic])
    # Broaden if the topic alone is thin.
    if len(candidates) < 3:
        candidates += SESSIONS.search_sessions(["Agents", "Generative AI", "Amazon Bedrock"])
    alts = planning.recommend_alternatives(dropped, candidates)
    return {
        "dropped_session_id": dropped_session_id,
        "alternatives": [a.model_dump(mode="json") for a in alts],
        "recommended_alternative_id": alts[0].session.id if alts else None,
    }


# --------------------------------------------------------------------------- #
# explain_session_types
# --------------------------------------------------------------------------- #
@strands_tool
def explain_session_types() -> dict:
    """Explain re:Invent session types (Breakout, Workshop, Chalk Talk, etc.) and
    content levels (100-400). Use this to advise attendees on format choice,
    hands-on balance, and whether a session needs a reservation."""
    from app.providers import reference_data

    return {
        "session_types": reference_data.session_types(),
        "content_levels": reference_data.content_levels(),
    }


# --------------------------------------------------------------------------- #
# import_session_catalog
# --------------------------------------------------------------------------- #
@strands_tool
def import_session_catalog(catalog_text: str, fmt: str = "json") -> dict:
    """Import a re:Invent session catalog that the attendee exported from the
    official catalog (JSON or CSV text). Replaces the active session source with
    the real catalog. Returns how many sessions were loaded."""
    count = load_catalog_text(catalog_text, fmt)
    return {
        "imported": count,
        "session_source": getattr(SESSIONS, "source", "demo"),
    }


@strands_tool
def retrieve_tips(query: str, top_k: int = 4) -> dict:
    """Retrieve relevant PAST re:Invent experience & preparation tips for a
    natural-language goal or question (RAG over the tips knowledge base). Use
    this to give grounded, cited preparation advice — only surface tips that
    exist in the knowledge base; do not invent advice."""
    from app.engine import knowledge

    return knowledge.advise(query, top_k)


def load_catalog_text(catalog_text: str, fmt: str = "json") -> int:
    """Parse pasted catalog text and load it into the active session provider."""
    from app.providers.catalog_provider import load_catalog_from_text

    sessions = load_catalog_from_text(catalog_text, fmt)
    if not sessions:
        return 0
    if hasattr(SESSIONS, "load_sessions"):
        SESSIONS.load_sessions(sessions)
    return len(sessions)


# Registry used by the deterministic orchestrator and exposed to Strands.
ALL_TOOLS = [
    search_flights,
    search_hotels,
    search_sessions,
    search_sessions_semantic,
    get_session_details,
    check_session_conflicts,
    estimate_travel_time,
    build_daily_schedule,
    generate_preparation_checklist,
    recommend_alternatives,
    explain_session_types,
    import_session_catalog,
    retrieve_tips,
]
