"""The Navigator — Re:Route AI's orchestration layer.

AWS Strands Agents is the orchestrator of record. When a Bedrock model and AWS
credentials are configured (set REROUTE_USE_STRANDS_MODEL=1), `orchestrate_plan`
and `orchestrate_reroute` run the real `strands.Agent`, which drives its own
tool-calling loop over the `@tool` functions in `tools.py` and returns our
Pydantic models via Strands `structured_output`.

When no model is configured (common in local/hackathon dev), the same tools are
executed by a deterministic pipeline so the demo is always reliable. Either way
the framework is genuinely wired — the tools, system prompt and agent are the
Strands ones. The pipeline mirrors the agent's multi-step reasoning:
Navigator → Session Scout → Route Planner → Wayfinder → (Recovery Navigator).
"""
from __future__ import annotations

from datetime import datetime

from app.agent import tools
from app.agent import strands_agent
from app.engine import planning
from app.models import (
    AgentEvent,
    Alternative,
    Plan,
    RerouteResult,
    Session,
    SessionStatus,
    TripPreferences,
    TripSummary,
)
from app.providers import demo_data

SYSTEM_PROMPT = """You are the Navigator for Re:Route AI, an autonomous assistant
for AWS re:Invent attendees. Your job is to protect the attendee's LEARNING GOAL,
not to maximize the number of sessions. The destination stays the same; the route
can change.

You coordinate specialized capabilities exposed as tools: search_flights,
search_hotels, search_sessions, check_session_conflicts, estimate_travel_time,
build_daily_schedule, generate_preparation_checklist, recommend_alternatives.

Plan for a real human: respect walking limits, buffers between venues, breaks,
and lunch. When a session becomes full or cancelled, find the best same-topic
alternative and explain briefly why it protects the learning goal. Never claim
real-time availability — demo data is simulated. Keep explanations short.
"""


def build_strands_agent():  # pragma: no cover - requires optional dependency + creds
    """Return the real Strands Agent (Bedrock-backed) if constructible, else None."""
    return strands_agent.get_agent()


# --------------------------------------------------------------------------- #
# Natural-language intent parsing (lightweight, deterministic)
# --------------------------------------------------------------------------- #
_TOPIC_KEYWORDS = {
    "Generative AI": ["generative ai", "gen ai", "genai", "llm"],
    "Agents": ["agent", "agents", "agentic"],
    "Amazon Bedrock": ["bedrock"],
    "Amazon SageMaker": ["sagemaker"],
    "Serverless": ["serverless", "lambda"],
    "Containers": ["container", "eks", "ecs", "kubernetes"],
    "Data": ["data", "analytics", "database"],
    "Security": ["security", "secure"],
    "Networking": ["network", "networking"],
    "Architecture": ["architecture", "well-architected"],
}
_CITY_HINTS = ["chennai", "bangalore", "mumbai", "delhi", "hyderabad", "london", "tokyo", "sydney"]


def parse_mission(text: str, base: TripPreferences | None = None) -> TripPreferences:
    prefs = base or TripPreferences()
    t = (text or "").lower()

    topics = [name for name, kws in _TOPIC_KEYWORDS.items() if any(k in t for k in kws)]
    # "Agentic AI" / "production AI" implies the Generative AI foundation too, so
    # related hands-on GenAI sessions are considered.
    if "Agents" in topics and "Generative AI" not in topics and ("ai" in t or "genai" in t):
        topics.append("Generative AI")
    if topics:
        prefs.topics = topics
        prefs.learning_goal = " and ".join(topics)

    for city in _CITY_HINTS:
        if city in t:
            prefs.origin = city.capitalize()
            break

    if "two day" in t or "2 day" in t:
        prefs.arrive_days_early = 2
    elif "one day early" in t or "1 day early" in t or "day early" in t:
        prefs.arrive_days_early = 1

    if "reasonable" in t or "budget" in t:
        prefs.hotel_budget_per_night = prefs.hotel_budget_per_night or 200
    if "near" in t and "venue" in t:
        prefs.preferred_hotel_area = "near venues"
    if "evening" in t:
        prefs.preferred_flight_time = "evening"
    elif "morning" in t:
        prefs.preferred_flight_time = "morning"

    return prefs


# --------------------------------------------------------------------------- #
# Public dispatchers — prefer the real Strands agent, else deterministic.
# --------------------------------------------------------------------------- #
def orchestrate_plan(mission_text: str, prefs: TripPreferences | None = None) -> Plan:
    """Plan the trip. Uses the real Strands Bedrock agent when configured."""
    if strands_agent.model_available():
        try:
            plan = strands_agent.run_agent_plan(mission_text)
            _tag_orchestrator(plan.agent_activity, "strands")
            return plan
        except Exception as exc:  # pragma: no cover - network/creds dependent
            # Never break the demo: fall back to the deterministic pipeline.
            plan = _deterministic_plan(mission_text, prefs)
            plan.recommendations.insert(
                0, f"(Strands model call failed, used deterministic pipeline: {type(exc).__name__})"
            )
            return plan
    return _deterministic_plan(mission_text, prefs)


def orchestrate_reroute(
    dropped_session_id: str,
    current_selected_ids: list[str],
    reason: str = "Session is no longer available",
) -> RerouteResult:
    if strands_agent.model_available():
        try:
            result = strands_agent.run_agent_reroute(
                dropped_session_id, current_selected_ids, reason
            )
            _tag_orchestrator(result.agent_activity, "strands")
            return result
        except Exception:  # pragma: no cover
            return _deterministic_reroute(dropped_session_id, current_selected_ids, reason)
    return _deterministic_reroute(dropped_session_id, current_selected_ids, reason)


def _tag_orchestrator(activity: list[AgentEvent], mode: str) -> None:
    if mode == "strands" and activity:
        activity.insert(
            0,
            AgentEvent(
                agent="Navigator",
                icon="🧭",
                task="Orchestrate with AWS Strands Agents",
                action=f"Bedrock model drove the tool-calling loop ({strands_agent.DEFAULT_MODEL_ID})",
                result="Live Strands agent orchestration",
            ),
        )


# --------------------------------------------------------------------------- #
# Plan A / B / C — three ranked itinerary variants from one mission.
# "Always have backups": A = ideal, B = backup, C = low-risk.
# --------------------------------------------------------------------------- #
def build_abc_plans(mission_text: str, prefs: TripPreferences | None = None) -> dict:
    prefs = parse_mission(mission_text, prefs) if mission_text else (prefs or TripPreferences())
    topics = prefs.topics or ["Generative AI", "Agents", "Amazon Bedrock"]
    found = tools.SESSIONS.search_sessions(topics)
    if mission_text and found:
        from app.engine import semantic
        found = semantic.semantic_search(mission_text, found)

    plan_a_sel = planning.select_non_conflicting(found, tools.VENUES, prefs.topics, max_per_day=4)
    a_ids = {s.id for s in plan_a_sel}

    variants = [
        {
            "key": "A", "label": "Plan A — Ideal",
            "rationale": "Your highest learning-match sessions. The plan you'd run if everything is available.",
            "select": lambda: plan_a_sel,
        },
        {
            "key": "B", "label": "Plan B — Backup",
            "rationale": "A genuine alternative route that avoids Plan A's picks and prefers repeats — the plan you switch to when your top sessions are full or cancelled.",
            "select": lambda: _select_backup(found, prefs, avoid_ids=a_ids),
        },
        {
            "key": "C", "label": "Plan C — Low-risk",
            "rationale": "Fewer venue hops and more hands-on, capped for a sustainable day. The one that survives Vegas traffic and a tough week.",
            "select": lambda: _select_lowrisk(found, prefs),
        },
    ]

    # Ground each plan with a relevant tip from the RAG knowledge base.
    tip_queries = {
        "A": f"best sessions for {prefs.learning_goal}",
        "B": "backup plan when sessions are full or cancelled",
        "C": "travel time between venues, avoid burnout, fewer venue hops",
    }
    plan_tips: dict[str, str] = {}
    try:
        from app.engine import knowledge
        for k, q in tip_queries.items():
            hits = knowledge.get_kb().retrieve(q, top_k=1)
            if hits:
                plan_tips[k] = hits[0].text
    except Exception:
        pass

    out = []
    for v in variants:
        selected = v["select"]()
        plan = _assemble_plan_from_selected(selected, prefs, label=v["label"])
        out.append({
            "key": v["key"],
            "label": v["label"],
            "rationale": v["rationale"],
            "tip": plan_tips.get(v["key"], ""),
            "plan": plan.model_dump(mode="json"),
            "summary": {
                "sessions": len(plan.sessions),
                "journey_score": plan.scores.journey_score,
                "route_quality": plan.scores.route_quality,
                "walking_km": round(sum(d.walking_km for d in plan.daily_schedule), 1),
                "venue_changes": sum(d.venue_changes for d in plan.daily_schedule),
                "hands_on": plan.scores.breakdown.get("Hands-on", 0),
            },
        })
    return {"mission": mission_text, "goal": prefs.learning_goal, "plans": out}


def _select_backup(found: list[Session], prefs: TripPreferences, avoid_ids: set[str] | None = None) -> list[Session]:
    """Backup: the route you'd run if your top picks fall through. Excludes FULL
    sessions, prefers repeats/alternatives, and de-prioritizes Plan A's picks so
    it's a genuinely different route (fills empty slots with A's picks only if
    nothing else fits)."""
    from copy import deepcopy

    from app.models import SessionStatus

    avoid_ids = avoid_ids or set()
    pool = [deepcopy(s) for s in found if s.status != SessionStatus.FULL]
    for s in pool:
        if "repeat" in s.title.lower() or s.status == SessionStatus.REPEAT_AVAILABLE:
            s.match_score = min(100, s.match_score + 10)
        # Push Plan A's exact picks to the back so alternatives win first.
        if s.id in avoid_ids:
            s.match_score = max(0, s.match_score - 40)
    return planning.select_non_conflicting(pool, tools.VENUES, prefs.topics, max_per_day=4)


def _select_lowrisk(found: list[Session], prefs: TripPreferences) -> list[Session]:
    """Low-risk: fewer sessions per day (less travel), hands-on emphasis."""
    # Ensure the goal is treated as implementation so hands-on formats are boosted.
    topics = list(prefs.topics) + ["build"]
    return planning.select_non_conflicting(found, tools.VENUES, topics, max_per_day=3)


def _assemble_plan_from_selected(selected: list[Session], prefs: TripPreferences, label: str) -> Plan:
    """Turn a selected session set into a full Plan (schedule, travel, scores,
    checklist, flights, hotel) — shared by the A/B/C variants."""
    from app.models import (
        ChecklistSection,
        FlightRecommendation,
        HotelRecommendation,
    )

    conflicts = planning.detect_conflicts(selected, tools.VENUES)
    schedules = planning.build_daily_schedule(selected, tools.VENUES)
    travel_legs = []
    by_day: dict[str, list[Session]] = {}
    for s in selected:
        by_day.setdefault(s.day, []).append(s)
    for day_sessions in by_day.values():
        travel_legs += planning.build_travel_legs(day_sessions, tools.VENUES)

    flight_recs = [FlightRecommendation(**r) for r in
                   tools.search_flights(prefs.model_dump(mode="json")).get("flight_recommendations", [])]
    hotel_recs = [HotelRecommendation(**r) for r in
                  tools.search_hotels(prefs.model_dump(mode="json")).get("hotel_recommendations", [])]
    rec_flight = next((r for r in flight_recs if r.recommended), None)
    rec_hotel = next((r for r in hotel_recs if r.recommended), None)
    arrival_dt = rec_flight.flight.arrive if rec_flight else None
    schedules = [planning.build_arrival_day(prefs, arrival_dt)] + schedules

    checklist = [ChecklistSection(**s) for s in
                 tools.generate_preparation_checklist(rec_flight is not None, rec_hotel is not None)["preparation_checklist"]]
    scores = planning.compute_scores(
        selected, conflicts, [s for s in schedules if s.day != "Arrival Day"],
        prefs.topics, rec_flight is not None, rec_hotel is not None,
    )

    return Plan(
        trip=TripSummary(
            origin=prefs.origin, destination=prefs.destination,
            arrival_date=arrival_dt.date().isoformat() if arrival_dt else None,
            departure_date=rec_flight.flight.depart.date().isoformat() if rec_flight else None,
            learning_goal=prefs.learning_goal, demo_mode=True,
        ),
        flight_recommendations=flight_recs,
        hotel_recommendations=hotel_recs,
        sessions=selected,
        daily_schedule=schedules,
        travel_routes=travel_legs,
        conflicts=conflicts,
        preparation_checklist=checklist,
        scores=scores,
        agent_activity=[AgentEvent(
            agent="Route Planner", icon="🛣️", task=f"Build {label}",
            action="Selected and scheduled sessions for this variant",
            result=f"{len(selected)} sessions · journey {scores.journey_score}%",
        )],
        recommendations=[],
    )


# --------------------------------------------------------------------------- #
# Rebuild a plan from an explicit set of session ids (used by "Add to Route").
# --------------------------------------------------------------------------- #
def rebuild_plan_from_sessions(
    session_ids: list[str], prefs: TripPreferences | None = None,
    pinned_ids: set[str] | None = None,
) -> Plan:
    """Assemble a full Plan from a chosen set of sessions (conflict-resolved,
    scheduled, scored). Reuses the engine so behavior matches orchestrate_plan.
    `pinned_ids` are always kept when feasible (used by 'Add to Route')."""
    from app.models import (
        ChecklistSection,
        FlightRecommendation,
        HotelRecommendation,
    )

    prefs = prefs or TripPreferences()
    activity: list[AgentEvent] = []
    recommendations: list[str] = []

    picked = [s for sid in session_ids if (s := tools.SESSIONS.get_session(sid))]
    conflicts = planning.detect_conflicts(picked, tools.VENUES)
    selected = planning.select_non_conflicting(
        picked, tools.VENUES, prefs.topics, pinned_ids=pinned_ids
    )
    activity.append(AgentEvent(
        agent="Route Planner", icon="🛣️", task="Rebuild route",
        action=f"Re-checked {len(picked)} sessions for conflicts",
        result=f"Kept {len(selected)}; removed {len(picked) - len(selected)}",
    ))

    schedules = planning.build_daily_schedule(selected, tools.VENUES)
    travel_legs = []
    by_day: dict[str, list[Session]] = {}
    for s in selected:
        by_day.setdefault(s.day, []).append(s)
    for day_sessions in by_day.values():
        travel_legs += planning.build_travel_legs(day_sessions, tools.VENUES)

    flight_recs = [FlightRecommendation(**r) for r in
                   tools.search_flights(prefs.model_dump(mode="json")).get("flight_recommendations", [])]
    hotel_recs = [HotelRecommendation(**r) for r in
                  tools.search_hotels(prefs.model_dump(mode="json")).get("hotel_recommendations", [])]
    rec_flight = next((r for r in flight_recs if r.recommended), None)
    rec_hotel = next((r for r in hotel_recs if r.recommended), None)
    arrival_dt = rec_flight.flight.arrive if rec_flight else None
    schedules = [planning.build_arrival_day(prefs, arrival_dt)] + schedules

    checklist = [ChecklistSection(**s) for s in
                 tools.generate_preparation_checklist(rec_flight is not None, rec_hotel is not None)["preparation_checklist"]]
    scores = planning.compute_scores(
        selected, conflicts, [s for s in schedules if s.day != "Arrival Day"],
        prefs.topics, rec_flight is not None, rec_hotel is not None,
    )
    advice = planning.mode_balance_recommendation(scores.learning_mode_mix, prefs.topics)
    if advice:
        recommendations.append(advice)
    activity.append(AgentEvent(
        agent="Journey Analyst", icon="📊", task="Re-score the journey",
        action="Recomputed scores after the change",
        result=f"Route quality {scores.route_quality}% · Journey score {scores.journey_score}%",
    ))

    return Plan(
        trip=TripSummary(
            origin=prefs.origin, destination=prefs.destination,
            arrival_date=arrival_dt.date().isoformat() if arrival_dt else None,
            departure_date=rec_flight.flight.depart.date().isoformat() if rec_flight else None,
            learning_goal=prefs.learning_goal, demo_mode=True,
        ),
        flight_recommendations=flight_recs,
        hotel_recommendations=hotel_recs,
        sessions=selected,
        daily_schedule=schedules,
        travel_routes=travel_legs,
        conflicts=conflicts,
        preparation_checklist=checklist,
        scores=scores,
        agent_activity=activity,
        recommendations=recommendations,
    )


# --------------------------------------------------------------------------- #
# Deterministic full plan orchestration (tool-driven, model-free)
# --------------------------------------------------------------------------- #
def _deterministic_plan(mission_text: str, prefs: TripPreferences | None = None) -> Plan:
    prefs = parse_mission(mission_text, prefs) if mission_text else (prefs or TripPreferences())
    activity: list[AgentEvent] = []
    recommendations: list[str] = []

    # 1) Navigator understands the goal
    activity.append(
        AgentEvent(
            agent="Navigator",
            icon="🧭",
            task="Understand your learning goal",
            action="Parsed your mission and objectives",
            result=f"Goal: {prefs.learning_goal}; from {prefs.origin}",
        )
    )

    # 2) Session Scout finds sessions. When we have the raw mission text, rank by
    #    MEANING (embeddings) and blend into match_score; else keyword search.
    topics = prefs.topics or ["Generative AI", "Agents", "Amazon Bedrock"]
    sess_res = tools.search_sessions(topics)
    found = [Session(**s) for s in sess_res.get("sessions", [])]
    search_action = f"Searched catalog for {', '.join(topics)}"
    if mission_text and found:
        from app.engine import semantic

        found = semantic.semantic_search(mission_text, found)
        search_action = (
            f"Ranked candidates by meaning for your goal "
            f"({semantic.get_index().provider.name} embeddings)"
        )
    activity.append(
        AgentEvent(
            agent="Session Scout",
            icon="🔎",
            task="Find sessions matching your objective",
            action=search_action,
            result=f"Found {len(found)} candidate sessions",
        )
    )

    # 3) Route Planner resolves conflicts + selects (engine), with explanations
    conflicts = planning.detect_conflicts(found, tools.VENUES)
    selected = planning.select_non_conflicting(found, tools.VENUES, prefs.topics)
    selected, dropped = planning.explain_selection(selected, found, tools.VENUES, prefs.topics)
    activity.append(
        AgentEvent(
            agent="Route Planner",
            icon="🛣️",
            task="Check schedule conflicts",
            action=f"Compared {len(found)} sessions for overlaps and tight transitions",
            result=f"Set aside {len(dropped)}; kept {len(selected)} (each explained)",
        )
    )
    for c in conflicts:
        recommendations.append(c.recommendation)

    # 4) Wayfinder checks venue transitions + builds schedule (tools/engine)
    schedules = planning.build_daily_schedule(selected, tools.VENUES)
    travel_legs = []
    by_day: dict[str, list[Session]] = {}
    for s in selected:
        by_day.setdefault(s.day, []).append(s)
    for day_sessions in by_day.values():
        travel_legs += planning.build_travel_legs(day_sessions, tools.VENUES)
    total_walk = round(sum(d.walking_km for d in schedules), 1)
    activity.append(
        AgentEvent(
            agent="Wayfinder",
            icon="🧭",
            task="Check venue transitions",
            action="Estimated walking/travel time and buffers between venues",
            result=f"{len(travel_legs)} transitions; ~{total_walk} km walking planned",
        )
    )

    # 5) Flights + hotels (tool calls)
    flight_res = tools.search_flights(prefs.model_dump(mode="json"))
    hotel_res = tools.search_hotels(prefs.model_dump(mode="json"))
    from app.models import FlightRecommendation, HotelRecommendation

    flight_recs = [FlightRecommendation(**r) for r in flight_res.get("flight_recommendations", [])]
    hotel_recs = [HotelRecommendation(**r) for r in hotel_res.get("hotel_recommendations", [])]
    rec_flight = next((r for r in flight_recs if r.recommended), None)
    rec_hotel = next((r for r in hotel_recs if r.recommended), None)
    if rec_flight:
        recommendations.append(
            f"Flight: {rec_flight.flight.airline} — {rec_flight.reason}"
        )
    if rec_hotel:
        recommendations.append(f"Hotel: {rec_hotel.hotel.name} — {rec_hotel.reason}")

    # Prepend an arrival-day schedule based on the recommended flight
    arrival_dt = rec_flight.flight.arrive if rec_flight else None
    arrival_day = planning.build_arrival_day(prefs, arrival_dt)
    schedules = [arrival_day] + schedules

    # 6) Checklist (tool call)
    checklist_res = tools.generate_preparation_checklist(
        has_flight=rec_flight is not None, has_hotel=rec_hotel is not None
    )
    from app.models import ChecklistSection

    checklist = [ChecklistSection(**s) for s in checklist_res["preparation_checklist"]]

    # 7) Journey Analyst — multi-factor scores + learning-mode balance
    scores = planning.compute_scores(
        selected, conflicts, [s for s in schedules if s.day != "Arrival Day"],
        prefs.topics, rec_flight is not None, rec_hotel is not None,
    )
    mode_advice = planning.mode_balance_recommendation(scores.learning_mode_mix, prefs.topics)
    if mode_advice:
        recommendations.append(mode_advice)

    # RAG: ground 1-2 preparation recommendations in past re:Invent experience.
    try:
        from app.engine import knowledge

        adv = knowledge.advise(mission_text or prefs.learning_goal, top_k=2)
        for tip in adv.get("tips", [])[:2]:
            src = f" (source: {tip['source']})" if tip.get("source") else ""
            recommendations.append(f"Prep tip: {tip['text']}{src}")
        if adv.get("tips"):
            activity.append(
                AgentEvent(
                    agent="Navigator",
                    icon="📚",
                    task="Apply past re:Invent experience",
                    action=f"Retrieved {len(adv['tips'])} relevant preparation tips (RAG)",
                    result="Added grounded prep advice to your plan",
                )
            )
    except Exception:
        pass

    activity.append(
        AgentEvent(
            agent="Journey Analyst",
            icon="📊",
            task="Score the learning journey",
            action="Weighed goal alignment, coverage, hands-on, balance, recovery and capacity",
            result=f"Route quality {scores.route_quality}% · Journey score {scores.journey_score}%",
        )
    )
    activity.append(
        AgentEvent(
            agent="Navigator",
            icon="🧭",
            task="Recommended route ready",
            action="Assembled flights, hotel, sessions, schedule and checklist",
            result="Plan ready for review",
        )
    )

    trip = TripSummary(
        origin=prefs.origin,
        destination=prefs.destination,
        arrival_date=arrival_dt.date().isoformat() if arrival_dt else None,
        departure_date=rec_flight.flight.depart.date().isoformat() if rec_flight else None,
        learning_goal=prefs.learning_goal,
        demo_mode=True,
    )

    return Plan(
        trip=trip,
        flight_recommendations=flight_recs,
        hotel_recommendations=hotel_recs,
        sessions=selected,
        dropped_sessions=dropped,
        daily_schedule=schedules,
        travel_routes=travel_legs,
        conflicts=conflicts,
        preparation_checklist=checklist,
        scores=scores,
        agent_activity=activity,
        recommendations=recommendations,
    )


# --------------------------------------------------------------------------- #
# Deterministic ReRoute / recovery orchestration (tool-driven, model-free)
# --------------------------------------------------------------------------- #
def _deterministic_reroute(
    dropped_session_id: str,
    current_selected_ids: list[str],
    reason: str = "Session is no longer available",
) -> RerouteResult:
    """When a session becomes full/cancelled/missed, protect the learning goal."""
    activity: list[AgentEvent] = []
    dropped = tools.SESSIONS.get_session(dropped_session_id)

    activity.append(
        AgentEvent(
            agent="Navigator",
            icon="🧭",
            task="Detect route problem",
            action=f"'{dropped.title if dropped else dropped_session_id}' — {reason}",
            result="Learning objective still protected",
            status="active",
        )
    )

    # Recovery Navigator + Session Scout: find alternatives (tool call)
    alt_res = tools.recommend_alternatives(dropped_session_id)
    alternatives = [Alternative(**a) for a in alt_res.get("alternatives", [])]
    activity.append(
        AgentEvent(
            agent="Session Scout",
            icon="🔎",
            task="Find alternatives",
            action=f"Searched same-topic and fallback sessions",
            result=f"Found {len(alternatives)} alternatives",
        )
    )

    # Build 'before' and 'after' route metrics for human approval
    before_ids = list(current_selected_ids)
    after_ids = [sid for sid in current_selected_ids if sid != dropped_session_id]
    rec_alt_id = alt_res.get("recommended_alternative_id")
    if rec_alt_id:
        after_ids.append(rec_alt_id)

    before_metrics = _route_metrics(before_ids)
    after_metrics = _route_metrics(after_ids)

    activity.append(
        AgentEvent(
            agent="Wayfinder",
            icon="🧭",
            task="Check new route",
            action="Re-checked venue transitions for the alternative",
            result="New route is feasible",
        )
    )
    activity.append(
        AgentEvent(
            agent="Route Planner",
            icon="🛣️",
            task="Compare options",
            action="Compared current route vs. recovery route",
            result="Recovery route recommended",
            status="waiting",
        )
    )

    metrics = planning.compare_metrics(before_metrics, after_metrics)

    return RerouteResult(
        reason=reason,
        dropped_session_id=dropped_session_id,
        alternatives=alternatives,
        recommended_alternative_id=rec_alt_id,
        metrics=metrics,
        agent_activity=activity,
    )


def _route_metrics(session_ids: list[str]) -> dict:
    sessions = [s for sid in session_ids if (s := tools.SESSIONS.get_session(sid))]
    selected = planning.select_non_conflicting(sessions, tools.VENUES)
    schedules = planning.build_daily_schedule(selected, tools.VENUES) if selected else []
    learning = int(sum(s.match_score for s in selected) / len(selected)) if selected else 0
    walking = round(sum(d.walking_km for d in schedules), 1)
    venues = sum(d.venue_changes for d in schedules)
    breaks = sum(d.break_minutes for d in schedules)
    return {"learning": learning, "walking": walking, "venues": venues, "breaks": breaks}
