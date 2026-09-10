"""Provider interfaces.

Everything the agent needs from the outside world (flights, hotels, sessions,
venue geography, walking times) is defined here as an abstract interface. Demo
implementations live alongside; real providers (Amazon, official re:Invent
catalog, a routing API) can be added later by implementing the same protocol
without touching the agent or the UI.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import Flight, Hotel, Session, TripPreferences


class FlightProvider(ABC):
    @abstractmethod
    def search_flights(self, prefs: TripPreferences) -> list[Flight]:
        ...


class HotelProvider(ABC):
    @abstractmethod
    def search_hotels(self, prefs: TripPreferences) -> list[Hotel]:
        ...


class SessionProvider(ABC):
    @abstractmethod
    def search_sessions(
        self, topics: list[str], day: str | None = None, venue: str | None = None
    ) -> list[Session]:
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> Session | None:
        ...


class VenueProvider(ABC):
    """Geography + travel between venues."""

    @abstractmethod
    def travel(self, from_venue: str, to_venue: str) -> tuple[float, int, bool]:
        """Return (distance_km, walk_minutes, shuttle_available)."""
        ...

    @abstractmethod
    def walk_from_hotel(self, venue: str) -> tuple[float, int]:
        """Return (distance_km, walk_minutes) from the recommended hotel."""
        ...
