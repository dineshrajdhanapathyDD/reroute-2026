"""Planning engine.

Pure, testable functions that turn provider data + preferences into structured
plan pieces: flight/hotel recommendations, conflict detection, travel legs, a
daily schedule, human-capacity assessment, checklist and scores. No Strands and
no HTTP here — this is the deterministic brain the tools and agent call.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models import (
    Alternative,
    CapacityState,
    ChecklistItem,
    ChecklistSection,
    DaySchedule,
    Flight,
    FlightRecommendation,
    Hotel,
    HotelRecommendation,
    Priority,
    RouteChangeMetric,
    ScheduleItem,
    Scores,
    Session,
    SessionConflict,
    SessionStatus,
    TravelLeg,
    TripPreferences,
)
from app.providers.base import VenueProvider

BUFFER_MINUTES = 10  # safety buffer we always add to venue transitions
_PRIORITY_RANK = {Priority.MUST: 3, Priority.HIGH: 2, Priority.MEDIUM: 1, Priority.LOW: 0}


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%-I:%M %p") if hasattr(dt, "strftime") else str(dt)


def fmt_time(dt: datetime) -> str:
    """Cross-platform 12-hour time formatting (Windows has no %-I)."""
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


# --------------------------------------------------------------------------- #
# Flights
# --------------------------------------------------------------------------- #
def recommend_flights(
    flights: list[Flight], prefs: TripPreferences, first_session_start: datetime | None
) -> list[FlightRecommendation]:
    """Pick the best flight given the user wants to arrive before their first session.

    Rule: arriving the evening before (or earlier) beats arriving the same morning,
    because it removes the risk of missing an early session after a long haul.
    """
    recs: list[FlightRecommendation] = []
    best_idx = -1
    best_score = -1.0

    for i, f in enumerate(flights):
        reason_parts = []
        score = 0.0

        if first_session_start is not None:
            hours_before = (first_session_start - f.arrive).total_seconds() / 3600.0
            if hours_before >= 12:
                score += 40
                reason_parts.append(
                    "arrives the day before, leaving time to check in and rest"
                )
            elif hours_before >= 2:
                score += 15
                reason_parts.append("arrives with a tight but workable buffer")
            else:
                reason_parts.append(
                    "arrives too close to the first session — risky after a long flight"
                )

        # Fewer stops and lower price are nice-to-haves.
        score += max(0, 20 - f.stops * 8)
        score += max(0, 25 - (f.price_usd - 900) / 40)
        if f.stops == 1:
            reason_parts.append("only one stop")

        recs.append(
            FlightRecommendation(
                flight=f,
                recommended=False,
                reason="; ".join(reason_parts).capitalize() or "Option available.",
            )
        )
        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx >= 0:
        recs[best_idx].recommended = True
    return recs


# --------------------------------------------------------------------------- #
# Hotels
# --------------------------------------------------------------------------- #
def recommend_hotels(hotels: list[Hotel], prefs: TripPreferences) -> list[HotelRecommendation]:
    recs: list[HotelRecommendation] = []
    best_idx = -1
    best_score = -1e9
    budget = prefs.hotel_budget_per_night

    for i, h in enumerate(hotels):
        # Balance convenience (walking) against price. Lower is better on both.
        walk_penalty = h.walk_minutes_to_main_venue * 4
        price_penalty = h.price_per_night_usd
        over_budget = budget is not None and h.price_per_night_usd > budget
        score = -(walk_penalty + price_penalty) + h.rating * 20
        if over_budget:
            score -= 200

        reason_parts = [f"{h.walk_minutes_to_main_venue} min walk to the main venue"]
        if budget is not None and not over_budget:
            reason_parts.append("within your budget")
        if h.walk_minutes_to_main_venue <= 5:
            reason_parts.append("closest to your highest-priority sessions")

        recs.append(
            HotelRecommendation(
                hotel=h,
                recommended=False,
                reason="; ".join(reason_parts).capitalize() + ".",
            )
        )
        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx >= 0:
        recs[best_idx].recommended = True
        recs[best_idx].reason = (
            "Recommended: within walking distance of your highest-priority sessions "
            "and reduces daily travel time"
            + (", while staying in budget." if budget else ".")
        )
    return recs


# --------------------------------------------------------------------------- #
# Conflicts
# --------------------------------------------------------------------------- #
def _overlaps(a: Session, b: Session) -> bool:
    return a.start < b.end and b.start < a.end


def detect_conflicts(
    sessions: list[Session], venues: VenueProvider
) -> list[SessionConflict]:
    """Detect two kinds of conflict:

    1. Direct time overlap.
    2. Infeasible transition — back-to-back sessions at different venues where
       the walking/travel time (plus buffer) exceeds the gap between them.
    """
    conflicts: list[SessionConflict] = []
    ordered = sorted(sessions, key=lambda s: s.start)
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if a.day != b.day:
                continue
            reason = None
            if _overlaps(a, b):
                reason = "Time overlap"
            else:
                gap_min = (b.start - a.end).total_seconds() / 60.0
                _, walk_min, _ = venues.travel(a.venue, b.venue)
                if a.venue != b.venue and gap_min < walk_min + BUFFER_MINUTES:
                    reason = (
                        f"Transition too tight: {int(walk_min)} min travel "
                        f"{a.venue}→{b.venue} but only {int(gap_min)} min gap"
                    )
            if reason:
                keep, drop = _resolve_priority(a, b)
                conflicts.append(
                    SessionConflict(
                        session_a_id=a.id,
                        session_b_id=b.id,
                        reason=reason,
                        keep_session_id=keep.id,
                        drop_session_id=drop.id,
                        recommendation=(
                            f"Attend '{keep.title}' (higher priority / match). "
                            f"Move '{drop.title}' to an alternative."
                        ),
                    )
                )
    return conflicts


def _resolve_priority(a: Session, b: Session) -> tuple[Session, Session]:
    ra, rb = _PRIORITY_RANK[a.priority], _PRIORITY_RANK[b.priority]
    if ra != rb:
        return (a, b) if ra > rb else (b, a)
    return (a, b) if a.match_score >= b.match_score else (b, a)


def _goal_wants_handson(goal_topics: list[str] | None) -> bool:
    text = " ".join(goal_topics or []).lower()
    return any(k in text for k in ("agent", "serverless", "build", "production", "implement", "hands"))


def _selection_value(s: Session, handson_boost: bool) -> float:
    """Ranking value. When the goal implies implementation, hands-on formats get
    a boost so the route isn't all lecture-style (spec: Workshop > Breakout is
    NOT always true — it depends on the learning goal)."""
    value = _PRIORITY_RANK[s.priority] * 100 + s.match_score
    if handson_boost and s.hands_on:
        value += 25
    return value


MAX_SESSIONS_PER_DAY = 4  # a sustainable ceiling for a real human


def select_non_conflicting(
    sessions: list[Session], venues: VenueProvider, goal_topics: list[str] | None = None,
    max_per_day: int = MAX_SESSIONS_PER_DAY, pinned_ids: set[str] | None = None,
) -> list[Session]:
    """Greedy selection: keep the highest-value sessions that don't conflict.

    Goal-aware: if the goal implies implementation, hands-on formats (workshops,
    builders' sessions, chalk/code talks) are weighted higher. Caps sessions per
    day so the route stays sustainable — the best route for a real human, not the
    maximum number of sessions.
    """
    handson_boost = _goal_wants_handson(goal_topics)
    pinned_ids = pinned_ids or set()
    # Pinned (user-chosen) sessions rank first and bypass the per-day cap so an
    # explicit "Add to Route" is always honored when feasible.
    ranked = sorted(
        sessions,
        key=lambda s: (s.id in pinned_ids, _selection_value(s, handson_boost)),
        reverse=True,
    )
    chosen: list[Session] = []
    per_day: dict[str, int] = {}
    for cand in ranked:
        if cand.status == SessionStatus.CANCELLED:
            continue
        if cand.id not in pinned_ids and per_day.get(cand.day, 0) >= max_per_day:
            continue
        ok = True
        for kept in chosen:
            if kept.day != cand.day:
                continue
            if _overlaps(kept, cand):
                ok = False
                break
            earlier, later = (kept, cand) if kept.start <= cand.start else (cand, kept)
            gap_min = (later.start - earlier.end).total_seconds() / 60.0
            if earlier.venue != later.venue:
                _, walk_min, _ = venues.travel(earlier.venue, later.venue)
                if gap_min < walk_min + BUFFER_MINUTES:
                    ok = False
                    break
        if ok:
            chosen.append(cand)
            per_day[cand.day] = per_day.get(cand.day, 0) + 1

    # Format diversity: if the goal wants hands-on but the route has none, try to
    # swap in the best hands-on session that fits (spec: don't build an all-lecture
    # route for an implementation goal).
    if handson_boost and not any(s.hands_on for s in chosen):
        chosen = _ensure_handson(chosen, ranked, venues)

    chosen.sort(key=lambda s: (s.day, s.start))
    return chosen


def _fits(cand: Session, others: list[Session], venues: VenueProvider) -> bool:
    for kept in others:
        if kept.day != cand.day:
            continue
        if _overlaps(kept, cand):
            return False
        earlier, later = (kept, cand) if kept.start <= cand.start else (cand, kept)
        gap_min = (later.start - earlier.end).total_seconds() / 60.0
        if earlier.venue != later.venue:
            _, walk_min, _ = venues.travel(earlier.venue, later.venue)
            if gap_min < walk_min + BUFFER_MINUTES:
                return False
    return True


def _ensure_handson(
    chosen: list[Session], ranked: list[Session], venues: VenueProvider
) -> list[Session]:
    """Try to introduce one hands-on session, dropping at most one lower-value
    non-hands-on session if needed to make room."""
    handson = [s for s in ranked if s.hands_on and s.status != SessionStatus.CANCELLED]
    for cand in handson:
        if _fits(cand, chosen, venues):
            return chosen + [cand]
    # Otherwise, drop the lowest-value droppable lecture session to fit the best workshop.
    for cand in handson:
        droppable = sorted(
            [s for s in chosen if not s.hands_on and s.priority != Priority.MUST],
            key=lambda s: s.match_score,
        )
        for victim in droppable:
            trial = [s for s in chosen if s.id != victim.id]
            if _fits(cand, trial, venues):
                return trial + [cand]
    return chosen


# --------------------------------------------------------------------------- #
# Travel legs (Wayfinder)
# --------------------------------------------------------------------------- #
def explain_selection(
    selected: list[Session], candidates: list[Session], venues: VenueProvider,
    goal_topics: list[str] | None = None,
) -> tuple[list[Session], list["object"]]:
    """Attach a short 'why' to each kept session and return (kept, dropped[]).

    dropped items are lightweight dicts {id,title,reason} explaining what the
    agent set aside (time overlap / infeasible venue transition / day full).
    """
    from app.models import DroppedSession

    handson = _goal_wants_handson(goal_topics)
    kept_ids = {s.id for s in selected}

    # 'Why kept' for each selected session.
    for s in selected:
        parts = [f"{s.match_score}% match to your goal"]
        if s.hands_on:
            parts.append("hands-on")
        if handson and s.hands_on:
            parts.insert(0, "fits your implementation goal")
        parts.append(f"feasible at {s.venue}")
        s.why = "; ".join(parts).capitalize() + "."

    # 'Why dropped' — only surface NOTABLE drops (conflicts, tight transitions,
    # day-full), not the long tail of lower-match sessions. Prefer high-match
    # candidates so the UI shows meaningful "set aside" decisions.
    dropped: list[DroppedSession] = []
    seen: set[str] = set()
    for c in sorted(candidates, key=lambda x: x.match_score, reverse=True):
        if c.id in kept_ids or c.id in seen or c.status == SessionStatus.CANCELLED:
            continue
        reason = _drop_reason(c, selected, venues)
        if reason.startswith("Lower learning-match"):
            continue  # skip the uninteresting bulk
        seen.add(c.id)
        dropped.append(DroppedSession(id=c.id, title=c.title, reason=reason))
        if len(dropped) >= 8:
            break
    return selected, dropped


def _drop_reason(cand: Session, chosen: list[Session], venues: VenueProvider) -> str:
    for kept in chosen:
        if kept.day != cand.day:
            continue
        if _overlaps(kept, cand):
            return f"Time overlap with '{kept.title[:40]}'"
        earlier, later = (kept, cand) if kept.start <= cand.start else (cand, kept)
        gap = (later.start - earlier.end).total_seconds() / 60.0
        if earlier.venue != later.venue:
            _, walk, _ = venues.travel(earlier.venue, later.venue)
            if gap < walk + BUFFER_MINUTES:
                return (f"Tight transition: {int(walk)} min {earlier.venue}→{later.venue}, "
                        f"only {int(gap)} min gap")
    # If it didn't conflict, it lost the per-day cap or ranking.
    same_day = sum(1 for k in chosen if k.day == cand.day)
    if same_day >= MAX_SESSIONS_PER_DAY:
        return f"{cand.day} already has {same_day} sessions (kept it sustainable)"
    return "Lower learning-match than the kept sessions"


def build_travel_legs(
    day_sessions: list[Session], venues: VenueProvider
) -> list[TravelLeg]:
    legs: list[TravelLeg] = []
    ordered = sorted(day_sessions, key=lambda s: s.start)
    for a, b in zip(ordered, ordered[1:]):
        if a.venue == b.venue:
            continue
        dist, walk_min, shuttle = venues.travel(a.venue, b.venue)
        depart = a.end
        arrival = depart + timedelta(minutes=walk_min)
        legs.append(
            TravelLeg(
                from_venue=a.venue,
                to_venue=b.venue,
                from_session_id=a.id,
                to_session_id=b.id,
                distance_km=dist,
                walk_minutes=walk_min,
                shuttle_available=shuttle,
                recommended_depart=depart,
                arrival=arrival,
                buffer_minutes=max(0, int((b.start - arrival).total_seconds() / 60)),
            )
        )
    return legs


def estimate_travel_time(
    from_venue: str, to_venue: str, venues: VenueProvider
) -> tuple[float, int, bool]:
    return venues.travel(from_venue, to_venue)


# --------------------------------------------------------------------------- #
# Daily schedule
# --------------------------------------------------------------------------- #
def build_daily_schedule(
    selected: list[Session], venues: VenueProvider
) -> list[DaySchedule]:
    by_day: dict[str, list[Session]] = {}
    for s in selected:
        by_day.setdefault(s.day, []).append(s)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    schedules: list[DaySchedule] = []

    for day in sorted(by_day, key=lambda d: day_order.index(d) if d in day_order else 99):
        sessions = sorted(by_day[day], key=lambda s: s.start)
        items: list[ScheduleItem] = []
        walking_km = 0.0
        venue_changes = 0
        break_minutes = 0

        # Morning start
        items.append(ScheduleItem(time="8:00 AM", activity="Breakfast", kind="meal", icon="🍳"))

        # Walk from hotel to first venue
        first = sessions[0]
        hd, hm = venues.walk_from_hotel(first.venue)
        walking_km += hd
        if hm > 0:
            items.append(
                ScheduleItem(
                    time=fmt_time(first.start - timedelta(minutes=hm + BUFFER_MINUTES)),
                    activity=f"Walk from hotel to {first.venue} (~{hm} min)",
                    venue=first.venue,
                    kind="travel",
                    icon="🚶",
                )
            )

        prev: Session | None = None
        for s in sessions:
            if prev is not None:
                gap = (s.start - prev.end).total_seconds() / 60.0
                if prev.venue != s.venue:
                    dist, walk_min, shuttle = venues.travel(prev.venue, s.venue)
                    walking_km += dist
                    venue_changes += 1
                    icon = "🚌" if shuttle else "🚶"
                    items.append(
                        ScheduleItem(
                            time=fmt_time(prev.end),
                            activity=(
                                f"{'Shuttle' if shuttle else 'Walk'} {prev.venue} → "
                                f"{s.venue} (~{walk_min} min)"
                            ),
                            venue=s.venue,
                            kind="travel",
                            icon=icon,
                        )
                    )
                elif gap >= 15:
                    # Count a realistic break; a very large gap is free time, not
                    # a scheduled break, so cap what we attribute to "break".
                    counted = min(int(gap), 90)
                    break_minutes += counted
                    label = (
                        f"Break ({int(gap)} min)" if gap <= 90
                        else f"Open time ({int(gap)} min) — rest / expo / networking"
                    )
                    items.append(
                        ScheduleItem(
                            time=fmt_time(prev.end),
                            activity=label,
                            kind="break",
                            icon="☕",
                        )
                    )

            # Lunch insertion around midday if there's a gap
            if prev and prev.end.hour < 12 <= s.start.hour:
                items.append(
                    ScheduleItem(time="12:00 PM", activity="Lunch", kind="meal", icon="🥗")
                )
                break_minutes += 45

            items.append(
                ScheduleItem(
                    time=fmt_time(s.start),
                    activity=s.title,
                    venue=f"{s.venue} · {s.room}",
                    session_id=s.id,
                    kind="session",
                    icon="🎤" if s.format == "Breakout" else "🛠️",
                )
            )
            prev = s

        # Networking + return to hotel
        items.append(
            ScheduleItem(time="5:00 PM", activity="Networking", kind="break", icon="🤝")
        )
        networking_minutes = 60
        last = sessions[-1]
        rd, rm = venues.walk_from_hotel(last.venue)
        walking_km += rd
        items.append(
            ScheduleItem(
                time=fmt_time(last.end + timedelta(minutes=90)),
                activity=f"Return to hotel (~{rm} min)",
                kind="travel",
                icon="🏨",
            )
        )

        schedules.append(
            DaySchedule(
                day=day,
                items=items,
                walking_km=round(walking_km, 1),
                venue_changes=venue_changes,
                break_minutes=break_minutes,
                networking_minutes=networking_minutes,
                capacity=assess_capacity(
                    len(sessions), walking_km, venue_changes, break_minutes
                ),
            )
        )

    return schedules


def build_arrival_day(prefs: TripPreferences, arrival: datetime | None) -> DaySchedule:
    """A light 'arrival day' schedule (the day before sessions start)."""
    t = fmt_time(arrival) if arrival else "4:30 PM"
    items = [
        ScheduleItem(time=t, activity=f"Arrive in {prefs.destination}", kind="arrival", icon="✈️"),
        ScheduleItem(time="6:00 PM", activity="Hotel check-in", kind="hotel", icon="🏨"),
        ScheduleItem(time="7:00 PM", activity="Explore nearby re:Invent venue", kind="break", icon="📍"),
        ScheduleItem(time="8:00 PM", activity="Prepare for tomorrow's sessions", kind="prep", icon="📝"),
    ]
    return DaySchedule(
        day="Arrival Day",
        items=items,
        walking_km=0.5,
        venue_changes=0,
        break_minutes=120,
        networking_minutes=0,
        capacity=CapacityState.SUSTAINABLE,
    )


# --------------------------------------------------------------------------- #
# Human capacity
# --------------------------------------------------------------------------- #
def assess_capacity(
    session_count: int, walking_km: float, venue_changes: int, break_minutes: int
) -> CapacityState:
    load = 0
    if session_count >= 6:
        load += 2
    elif session_count >= 4:
        load += 1
    if walking_km > 8:
        load += 2
    elif walking_km > 6:
        load += 1
    if venue_changes >= 4:
        load += 2
    elif venue_changes >= 3:
        load += 1
    if break_minutes < 30:
        load += 1
    if load >= 4:
        return CapacityState.OVERLOADED
    if load >= 2:
        return CapacityState.BUSY
    return CapacityState.SUSTAINABLE


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #
def generate_checklist(has_flight: bool, has_hotel: bool) -> list[ChecklistSection]:
    return [
        ChecklistSection(
            title="Before Departure",
            items=[
                ChecklistItem(label="Flight booked", done=has_flight),
                ChecklistItem(label="Hotel booked", done=has_hotel),
                ChecklistItem(label="Event registration confirmed"),
                ChecklistItem(label="Important sessions saved"),
                ChecklistItem(label="Travel documents checked (passport, visa/ESTA)"),
                ChecklistItem(label="Mobile connectivity / eSIM prepared"),
                ChecklistItem(label="Chargers & power bank packed"),
                ChecklistItem(label="AWS account ready"),
                ChecklistItem(label="Laptop prepared for workshops"),
                ChecklistItem(label="Business cards / networking info ready"),
            ],
        ),
        ChecklistSection(
            title="Before Each Event Day",
            items=[
                ChecklistItem(label="Review today's sessions"),
                ChecklistItem(label="Check venue locations"),
                ChecklistItem(label="Check walking routes"),
                ChecklistItem(label="Check session conflicts"),
                ChecklistItem(label="Confirm session priorities"),
                ChecklistItem(label="Check transportation / shuttle conditions"),
            ],
        ),
    ]


# --------------------------------------------------------------------------- #
# Scores
# --------------------------------------------------------------------------- #
def learning_mode_mix(selected: list[Session]) -> dict[str, int]:
    """Percentage split across the four learning modes."""
    from app.models import LEARNING_MODES, format_meta

    counts = {m: 0 for m in LEARNING_MODES}
    for s in selected:
        mode = s.learning_mode or format_meta(s.format)["mode"]
        counts[mode] = counts.get(mode, 0) + 1
    total = sum(counts.values()) or 1
    return {m: round(c * 100 / total) for m, c in counts.items()}


def mode_balance_recommendation(mix: dict[str, int], goal_topics: list[str]) -> str | None:
    """Navigator advice when the mode mix doesn't fit the goal.

    If the goal implies implementation but hands-on modes are low, suggest more
    hands-on. This is deliberate balancing, not maximizing sessions.
    """
    hands_on = mix.get("Build It Yourself", 0) + mix.get("Work Alongside Experts", 0)
    goal_text = " ".join(goal_topics).lower()
    wants_handson = any(k in goal_text for k in ("agent", "serverless", "build", "production", "implement"))
    if wants_handson and hands_on < 40:
        return (
            "Your goal is production implementation but your route is mostly "
            "lecture-style. Consider swapping one breakout for a workshop or "
            "builders' session to add hands-on learning."
        )
    if mix.get("Watch and Learn", 0) >= 70:
        return "Your route is heavily passive; a chalk talk or workshop would add depth."
    return None


def compute_scores(
    selected: list[Session],
    conflicts: list[SessionConflict],
    schedules: list[DaySchedule],
    goal_topics: list[str],
    has_flight: bool,
    has_hotel: bool,
) -> Scores:
    # Route quality: high match, few conflicts, sustainable days.
    avg_match = sum(s.match_score for s in selected) / len(selected) if selected else 0
    conflict_penalty = min(30, len(conflicts) * 10)
    overloaded = sum(1 for d in schedules if d.capacity == CapacityState.OVERLOADED)
    route_quality = int(max(0, min(100, avg_match - conflict_penalty - overloaded * 8)))

    # Category coverage per goal topic.
    coverage: dict[str, int] = {}
    topics = goal_topics or ["Agents", "Generative AI", "Amazon Bedrock"]
    for t in topics:
        matched = [s for s in selected if t.lower() in (s.topic + " " + s.title).lower()]
        coverage[t] = min(100, len(matched) * 50)
    cov_avg = int(sum(coverage.values()) / len(coverage)) if coverage else 0

    # --- Journey Analyst multi-factor breakdown --- #
    goal_alignment = int(avg_match)
    hands_on_sessions = [s for s in selected if s.hands_on]
    hands_on = min(100, round(len(hands_on_sessions) * 100 / max(1, len(selected)))) if selected else 0
    mix = learning_mode_mix(selected)
    active_modes = sum(1 for v in mix.values() if v > 0)
    format_balance = min(100, active_modes * 30 + 10)
    # Recovery capacity: do good same-topic fallbacks exist?
    recovery = 95 if selected else 60
    capacity_states = [d.capacity for d in schedules]
    cap_score = 100
    cap_score -= 25 * sum(1 for c in capacity_states if c == CapacityState.OVERLOADED)
    cap_score -= 8 * sum(1 for c in capacity_states if c == CapacityState.BUSY)
    human_capacity = max(0, min(100, cap_score))

    breakdown = {
        "Goal alignment": goal_alignment,
        "Coverage": cov_avg,
        "Hands-on": hands_on,
        "Format balance": format_balance,
        "Recovery": recovery,
        "Human capacity": human_capacity,
    }
    readiness_bonus = (has_flight + has_hotel) * 3  # small nudge for booked travel
    journey_score = int(max(0, min(100,
        0.30 * goal_alignment + 0.20 * cov_avg + 0.15 * hands_on +
        0.10 * format_balance + 0.10 * recovery + 0.15 * human_capacity + readiness_bonus,
    )))

    return Scores(
        journey_score=journey_score,
        route_quality=route_quality,
        learning_coverage=coverage,
        breakdown=breakdown,
        learning_mode_mix=mix,
    )


# --------------------------------------------------------------------------- #
# Alternatives / recovery
# --------------------------------------------------------------------------- #
def recommend_alternatives(
    dropped: Session, candidates: list[Session]
) -> list[Alternative]:
    """Find alternatives for a dropped/full/cancelled session, protecting the goal."""
    alts: list[Alternative] = []
    for c in candidates:
        if c.id == dropped.id or c.status == SessionStatus.CANCELLED:
            continue
        if c.topic.lower() != dropped.topic.lower() and c.match_score < 70:
            continue
        # Similarity: same topic + closeness of match score.
        same_topic = c.topic.lower() == dropped.topic.lower()
        sim = c.match_score - (0 if same_topic else 15)
        note = "Repeat session" if "repeat" in c.title.lower() else (
            "Hands-on workshop" if c.format == "Workshop" else "Related session"
        )
        alts.append(Alternative(session=c, match_score=max(0, min(100, sim)), note=note))
    alts.sort(key=lambda a: a.match_score, reverse=True)
    return alts[:3]


def compare_metrics(before: dict, after: dict) -> list[RouteChangeMetric]:
    def d(label, b, a, lower_is_better):
        direction = "same"
        if a != b:
            improved = (a < b) if lower_is_better else (a > b)
            direction = "up" if improved else "down"
        return RouteChangeMetric(label=label, before=str(b), after=str(a), direction=direction)

    return [
        d("Learning Score", before["learning"], after["learning"], lower_is_better=False),
        d("Walking (km)", before["walking"], after["walking"], lower_is_better=True),
        d("Venue Changes", before["venues"], after["venues"], lower_is_better=True),
        d("Break Time (min)", before["breaks"], after["breaks"], lower_is_better=False),
    ]
