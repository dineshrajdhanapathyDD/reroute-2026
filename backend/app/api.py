"""FastAPI app for Re:Route AI.

Endpoints return the structured Plan / RerouteResult models so the frontend can
render cards, timelines, maps, checklists and the agent-activity stream.
"""
from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import voice
from app.agent import navigator, strands_agent, tools
from app.models import (
    Plan,
    RerouteResult,
    SessionStatus,
    TripPreferences,
)

app = FastAPI(title="Re:Route AI", version="1.0.0")

# CORS: In production the AWS Lambda Function URL applies its own CORS config
# (AllowOrigins: ["*"]). If FastAPI's CORSMiddleware ALSO sets the header, the
# browser receives a duplicated `Access-Control-Allow-Origin` (e.g. "*, https://
# <cloudfront>"), which is invalid and makes fetch() fail. So we only enable the
# app-level CORS middleware when NOT running behind the Function URL. Local dev
# uses the Vite proxy (same-origin), so it needs no CORS either — but we enable
# it there for direct-to-:8000 access. Toggle with REROUTE_DISABLE_APP_CORS=1.
import os as _os

if _os.getenv("REROUTE_DISABLE_APP_CORS", "").lower() not in ("1", "true", "yes") and not _os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #
class MissionRequest(BaseModel):
    mission: str = ""
    preferences: TripPreferences | None = None


class RerouteRequest(BaseModel):
    dropped_session_id: str
    current_selected_ids: list[str] = []
    reason: str = "Session is no longer available"


class AvailabilityRequest(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.FULL


class ModelSelectRequest(BaseModel):
    model_key: str


class SpeakRequest(BaseModel):
    text: str
    voice_id: str | None = None


class CatalogImportRequest(BaseModel):
    catalog_text: str
    format: str = "json"  # "json" | "csv"


class LearningGraphRequest(BaseModel):
    goal_topics: list[str] = []
    selected_session_ids: list[str] = []
    attended_session_ids: list[str] = []


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict] = []


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    status = strands_agent.agent_status()
    session_source = getattr(tools.SESSIONS, "source", "demo")
    mcp_backed = session_source == "mcp"
    return {
        "status": "ok",
        "demo_mode": session_source not in ("catalog", "mcp"),
        "strands_available": tools.HAVE_STRANDS,
        # True only when the Bedrock-backed agent actually drives requests.
        "strands_model_orchestration": strands_agent.model_available(),
        "orchestrator": "strands-bedrock" if strands_agent.model_available() else "deterministic-tools",
        "session_source": session_source,  # "mcp" | "catalog" | "demo"
        "mcp_integration": mcp_backed,  # sessions served by reinvent2026-mcp
        "embedding_provider": _embed_provider_name(),
        "strands": status,
    }


@app.get("/api/mcp/status")
def mcp_status() -> dict:
    """Status of the reinvent2026-mcp integration (if the MCP provider is active)."""
    prov = tools.SESSIONS
    if hasattr(prov, "status") and getattr(prov, "source", "") == "mcp":
        return {"enabled": True, **prov.status()}
    return {
        "enabled": False,
        "note": "Set REROUTE_USE_MCP=1 to serve sessions from the reinvent2026-mcp server.",
        "session_source": getattr(prov, "source", "demo"),
    }


def _embed_provider_name() -> str:
    from app.providers import embeddings
    return embeddings.provider_name()


@app.get("/api/aws/status")
def aws_status() -> dict:
    """Which AWS services are live (Bedrock agent, Titan embeddings, Polly, MCP)
    and how to enable each. Everything degrades gracefully without credentials."""
    from app import aws_status as aws

    return aws.aws_status()


@app.get("/api/agent/status")
def agent_status() -> dict:
    """Detailed Strands agent wiring — which tools are registered, model id,
    whether the agent object was built, and any construction error."""
    return strands_agent.agent_status()


@app.post("/api/plan", response_model=Plan)
def create_plan(req: MissionRequest) -> Plan:
    """Run the full Navigator pipeline and return a structured plan."""
    return navigator.orchestrate_plan(req.mission, req.preferences)


class AddSessionRequest(BaseModel):
    current_selected_ids: list[str] = []
    session_id: str
    learning_goal: str = ""


@app.post("/api/plan/add-session", response_model=Plan)
def add_session(req: AddSessionRequest) -> Plan:
    """Add a catalog session to the current route and rebuild the plan
    (conflict-checked, re-scheduled, re-scored)."""
    ids = list(dict.fromkeys([*req.current_selected_ids, req.session_id]))  # de-dup, keep order
    prefs = TripPreferences()
    if req.learning_goal:
        prefs.learning_goal = req.learning_goal
        prefs.topics = [t.strip() for t in req.learning_goal.replace(" and ", ",").split(",") if t.strip()]
    # Pin the newly-added session so it's always kept when feasible.
    return navigator.rebuild_plan_from_sessions(ids, prefs, pinned_ids={req.session_id})


@app.post("/api/plans/abc")
def plans_abc(req: MissionRequest) -> dict:
    """Generate three ranked itinerary variants (Plan A ideal / B backup /
    C low-risk) from one mission, each with a rationale and score summary."""
    return navigator.build_abc_plans(req.mission, req.preferences)


@app.post("/api/reroute", response_model=RerouteResult)
def reroute(req: RerouteRequest) -> RerouteResult:
    """Recovery Navigator: find alternatives for a dropped session and produce a
    before/after comparison for human approval."""
    return navigator.orchestrate_reroute(
        req.dropped_session_id, req.current_selected_ids, req.reason
    )


@app.post("/api/demo/availability")
def set_availability(req: AvailabilityRequest) -> dict:
    """Demo control: flip a session's availability (full/cancelled) to trigger
    a ReRoute in the demo flow."""
    tools.SESSIONS.set_status(req.session_id, req.status)
    return {"session_id": req.session_id, "status": req.status}


@app.get("/api/sessions")
def list_sessions(topics: str = "") -> dict:
    """List sessions, optionally filtered by comma-separated topics."""
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    return tools.search_sessions(topic_list or ["Generative AI", "Agents", "Amazon Bedrock"])


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 8


@app.post("/api/sessions/semantic")
def sessions_semantic(req: SemanticSearchRequest) -> dict:
    """Semantic session search by natural-language learning goal (embeddings)."""
    return tools.search_sessions_semantic(req.query, req.top_k)


# --------------------------------------------------------------------------- #
# Session catalog: reference data + user import
# --------------------------------------------------------------------------- #
@app.post("/api/learning-graph")
def learning_graph(req: LearningGraphRequest) -> dict:
    """Build the learning graph with node states from the goal + selected sessions.

    If no session ids are supplied, the Navigator selects a route for the goal so
    the graph still reflects a realistic plan.
    """
    from app.engine import learning_graph as lg

    topics = req.goal_topics or ["Agents", "Generative AI", "Amazon Bedrock"]
    if req.selected_session_ids:
        selected = [s for sid in req.selected_session_ids if (s := tools.SESSIONS.get_session(sid))]
    else:
        found = tools.SESSIONS.search_sessions(topics)
        from app.engine import planning
        selected = planning.select_non_conflicting(found, tools.VENUES, topics)
    return lg.build_learning_graph(topics, selected, set(req.attended_session_ids))


@app.get("/api/official-links")
def official_links() -> dict:
    """Official AWS re:Invent 2026 links — source of truth for the UI."""
    from app.official_links import OFFICIAL_LINKS

    return OFFICIAL_LINKS


@app.get("/api/event")
def event_info() -> dict:
    """Real re:Invent 2026 event, venues, keynotes, Expo, security focus."""
    from app.providers import reinvent_data as rd

    return {
        "event": rd.EVENT,
        "venues": rd.VENUES,
        "keynotes": rd.KEYNOTES,
        "expo_activities": rd.EXPO_ACTIVITIES,
        "security_focus": rd.SECURITY_FOCUS,
        "experiences": rd.EXPERIENCES,
    }


class AdviceRequest(BaseModel):
    query: str = ""
    mission: str = ""
    top_k: int = 4


@app.post("/api/advice")
def advice(req: AdviceRequest) -> dict:
    """RAG preparation advice: retrieve relevant past-experience tips for a
    mission/query and return them with short grounded commentary."""
    from app.engine import knowledge

    q = (req.query or req.mission or "prepare for AWS re:Invent").strip()
    return knowledge.advise(q, req.top_k)


class AddTipsRequest(BaseModel):
    tips: list[dict]


@app.post("/api/advice/add")
def advice_add(req: AddTipsRequest) -> dict:
    """Add your own past-experience tips to the knowledge base at runtime.
    Each tip: {text, tags?, source?}."""
    from app.engine import knowledge

    total = knowledge.get_kb().add_tips(req.tips)
    return {"added": len(req.tips), "knowledge_count": total}


@app.get("/api/session-types")
def session_types() -> dict:
    """Static reference: re:Invent session types and content levels (100-400)."""
    from app.providers import reference_data

    return {
        "session_types": reference_data.session_types(),
        "content_levels": reference_data.content_levels(),
    }


@app.get("/api/catalog/status")
def catalog_status() -> dict:
    src = getattr(tools.SESSIONS, "source", "demo")
    total = len(tools.search_sessions([]).get("sessions", []))
    return {"session_source": src, "session_count": total, "demo": src != "catalog"}


@app.get("/api/catalog/facets")
def catalog_facets() -> dict:
    """Distinct dropdown options for the Session Explorer, computed from the
    full catalog: topics, levels, formats, venues, days, learning modes."""
    sessions = tools.SESSIONS.search_sessions([])

    def distinct(key):
        vals = sorted({getattr(s, key) for s in sessions if getattr(s, key)})
        return vals

    return {
        "total": len(sessions),
        "topics": distinct("topic"),
        "levels": distinct("level"),
        "formats": distinct("format"),
        "venues": distinct("venue"),
        "days": distinct("day"),
        "learning_modes": distinct("learning_mode"),
    }


@app.get("/api/catalog/filter")
def catalog_filter(
    topic: str = "",
    level: str = "",
    format: str = "",
    venue: str = "",
    day: str = "",
    learning_mode: str = "",
    text: str = "",
    hands_on: str = "",  # "" | "true" | "false"
    page: int = 1,
    limit: int = 24,
) -> dict:
    """Filter the full catalog by any combination of facets + free text.
    Returns a paginated slice plus the total match count."""
    sessions = tools.SESSIONS.search_sessions([])
    t = text.strip().lower()

    def keep(s) -> bool:
        if topic and s.topic != topic:
            return False
        if level and s.level != level:
            return False
        if format and s.format != format:
            return False
        if venue and s.venue != venue:
            return False
        if day and s.day != day:
            return False
        if learning_mode and s.learning_mode != learning_mode:
            return False
        if hands_on in ("true", "false") and str(s.hands_on).lower() != hands_on:
            return False
        if t:
            hay = (s.title + " " + s.topic + " " + getattr(s, "abstract", "")).lower()
            if t not in hay:
                return False
        return True

    matched = [s for s in sessions if keep(s)]
    matched.sort(key=lambda s: (-s.match_score, s.title))
    total = len(matched)
    page = max(1, page)
    limit = max(1, min(100, limit))
    start = (page - 1) * limit
    slice_ = matched[start:start + limit]
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "sessions": [s.model_dump(mode="json") for s in slice_],
    }


@app.post("/api/catalog/import")
def catalog_import(req: CatalogImportRequest) -> dict:
    """Import a catalog the attendee exported from the official re:Invent catalog
    (pasted JSON or CSV text). Replaces the active session source."""
    try:
        count = tools.load_catalog_text(req.catalog_text, req.format)
    except Exception as exc:  # noqa: BLE001
        return {"imported": 0, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "imported": count,
        "session_source": getattr(tools.SESSIONS, "source", "demo"),
    }


# --------------------------------------------------------------------------- #
# Model selection (Amazon Nova / Claude on Bedrock)
# --------------------------------------------------------------------------- #
@app.get("/api/models")
def list_models() -> dict:
    return {"active": strands_agent.active_model(), "available": strands_agent.list_models()}


@app.post("/api/models/select")
def select_model(req: ModelSelectRequest) -> dict:
    return strands_agent.select_model(req.model_key)


# --------------------------------------------------------------------------- #
# Voice (Amazon Polly TTS + config for browser STT/TTS fallback)
# --------------------------------------------------------------------------- #
@app.get("/api/voice/config")
def voice_config() -> dict:
    return voice.voice_config()


@app.post("/api/voice/speak")
def voice_speak(req: SpeakRequest):
    """Return MP3 audio (Amazon Polly). If Polly is unavailable, returns 204 so
    the frontend falls back to the browser's speech synthesis."""
    audio = voice.synthesize(req.text, req.voice_id)
    if audio is None:
        return Response(status_code=204)
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/voice/plan-summary")
def voice_plan_summary(plan: Plan) -> dict:
    """Build a short, speakable summary of a plan for hands-free readout."""
    return {"text": spoken_summary(plan)}


def spoken_summary(plan: Plan) -> str:
    """A concise, natural-language summary suitable for text-to-speech."""
    rec_flight = next((r for r in plan.flight_recommendations if r.recommended), None)
    rec_hotel = next((r for r in plan.hotel_recommendations if r.recommended), None)
    days = [d for d in plan.daily_schedule if d.day != "Arrival Day"]
    parts = [
        f"Here is your Re:Route plan for {plan.trip.learning_goal}.",
        f"Traveling from {plan.trip.origin} to {plan.trip.destination}.",
    ]
    if rec_flight:
        parts.append(f"Recommended flight: {rec_flight.flight.airline}.")
    if rec_hotel:
        parts.append(f"Recommended hotel: {rec_hotel.hotel.name}.")
    parts.append(f"I planned {len(plan.sessions)} sessions across {len(days)} days.")
    if plan.conflicts:
        parts.append(f"I resolved {len(plan.conflicts)} scheduling conflicts for you.")
    parts.append(
        f"Your journey score is {plan.scores.journey_score} percent, "
        f"and route quality is {plan.scores.route_quality} percent."
    )
    parts.append("Remember, the destination stays the same. The route can change.")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Conversational entry point — the newcomer-friendly chat.
# --------------------------------------------------------------------------- #
@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    """Talk to the Navigator in plain language. Detects intent (greeting, help,
    prep advice, session search, plan) and replies conversationally, reusing the
    same grounded engine capabilities (RAG advice, semantic search, planning)."""
    from app.engine import chat as chat_engine

    return chat_engine.chat(req.message, req.history)
