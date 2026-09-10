"""Demo implementations of the provider interfaces.

Swap these for real providers later by implementing the same base classes.
"""
from __future__ import annotations

from copy import deepcopy

from app.models import Flight, Hotel, Session, TripPreferences
from app.providers import demo_data
from app.providers.base import (
    FlightProvider,
    HotelProvider,
    SessionProvider,
    VenueProvider,
)


class DemoFlightProvider(FlightProvider):
    def search_flights(self, prefs: TripPreferences) -> list[Flight]:
        flights = deepcopy(demo_data.DEMO_FLIGHTS)
        # Optional preference filtering (morning/evening arrival)
        if prefs.preferred_flight_time == "evening":
            flights.sort(key=lambda f: 0 if f.arrive.hour >= 17 else 1)
        elif prefs.preferred_flight_time == "morning":
            flights.sort(key=lambda f: 0 if f.arrive.hour < 12 else 1)
        return flights


class DemoHotelProvider(HotelProvider):
    def search_hotels(self, prefs: TripPreferences) -> list[Hotel]:
        hotels = deepcopy(demo_data.DEMO_HOTELS)
        if prefs.hotel_budget_per_night:
            in_budget = [h for h in hotels if h.price_per_night_usd <= prefs.hotel_budget_per_night]
            # Keep at least the cheapest option so we never return empty on a tight budget.
            hotels = in_budget or sorted(hotels, key=lambda h: h.price_per_night_usd)[:1]
        return hotels


class DemoSessionProvider(SessionProvider):
    def __init__(self) -> None:
        from app.providers.enrich import enrich_all

        # Keep a mutable store so demo can flip availability (full/cancelled).
        self._sessions: dict[str, Session] = {
            s.id: s for s in enrich_all(deepcopy(demo_data.DEMO_SESSIONS))
        }

    def search_sessions(
        self, topics: list[str], day: str | None = None, venue: str | None = None
    ) -> list[Session]:
        topics_lower = [t.strip().lower() for t in topics if t.strip()]
        results: list[Session] = []
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

    def get_session(self, session_id: str) -> Session | None:
        s = self._sessions.get(session_id)
        return deepcopy(s) if s else None

    # Demo-only helpers to mutate availability
    def set_status(self, session_id: str, status) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].status = status


class DemoVenueProvider(VenueProvider):
    """Venue travel using the real re:Invent 2026 six-venue campus.

    Returns (distance_km, minutes, shuttle_used). For non-walkable pairs the
    minutes reflect the campus shuttle and shuttle_used is True; walkable pairs
    return the walking minutes.
    """

    def travel(self, from_venue: str, to_venue: str) -> tuple[float, int, bool]:
        from app.providers import reinvent_data

        t = reinvent_data.venue_travel(from_venue, to_venue)
        if not t["walkable"] and t["shuttle"] is not None:
            return t["km"], t["shuttle"], True
        return t["km"], t["walk"], False

    def walk_from_hotel(self, venue: str) -> tuple[float, int]:
        # The recommended hotel is treated as adjacent to The Venetian (main hub).
        km, minutes, _ = self.travel("The Venetian", venue)
        # add a short walk from the room to the session floor
        return km, max(minutes, 3)
