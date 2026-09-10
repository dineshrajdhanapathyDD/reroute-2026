"""Tests for the planning engine and agent tools."""
from __future__ import annotations

from datetime import datetime

import pytest

from app.agent import navigator, tools
from app.engine import planning
from app.models import Priority, Session, SessionStatus, TripPreferences
from app.providers.catalog_provider import CatalogSessionProvider
from app.providers.demo_providers import DemoSessionProvider, DemoVenueProvider


@pytest.fixture(autouse=True)
def _reset_sessions():
    """Ensure every test starts from the demo catalog (some tests import a
    catalog and mutate the shared provider)."""
    tools.SESSIONS = CatalogSessionProvider(path="does-not-exist.json")  # -> demo
    yield
    tools.SESSIONS = CatalogSessionProvider(path="does-not-exist.json")


def _sess(id, day, sh, sm, eh, em, venue, prio=Priority.MEDIUM, match=80):
    return Session(
        id=id, title=f"Session {id}", topic="Agents", format="Breakout",
        venue=venue, room="R1", day=day,
        start=datetime(2026, 12, 1, sh, sm), end=datetime(2026, 12, 1, eh, em),
        priority=prio, status=SessionStatus.AVAILABLE, match_score=match,
    )


VENUES = DemoVenueProvider()


# --------------------------------------------------------------------------- #
# Conflict detection
# --------------------------------------------------------------------------- #
def test_detects_time_overlap():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = _sess("b", "Tuesday", 9, 30, 10, 30, "Venetian")
    conflicts = planning.detect_conflicts([a, b], VENUES)
    assert len(conflicts) == 1
    assert conflicts[0].reason == "Time overlap"


def test_detects_infeasible_transition():
    # 10 min gap but MGM<->Venetian is ~45 min => infeasible.
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = _sess("b", "Tuesday", 10, 10, 11, 0, "MGM Grand")
    conflicts = planning.detect_conflicts([a, b], VENUES)
    assert len(conflicts) == 1
    assert "Transition too tight" in conflicts[0].reason


def test_feasible_transition_no_conflict():
    # Same venue, back to back => fine.
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = _sess("b", "Tuesday", 10, 15, 11, 0, "Venetian")
    assert planning.detect_conflicts([a, b], VENUES) == []


def test_no_conflict_across_days():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = Session(**{**a.model_dump(), "id": "b", "day": "Wednesday"})
    assert planning.detect_conflicts([a, b], VENUES) == []


def test_conflict_keeps_higher_priority():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian", prio=Priority.MUST)
    b = _sess("b", "Tuesday", 9, 30, 10, 30, "Venetian", prio=Priority.LOW)
    c = planning.detect_conflicts([a, b], VENUES)[0]
    assert c.keep_session_id == "a"
    assert c.drop_session_id == "b"


# --------------------------------------------------------------------------- #
# Non-conflicting selection
# --------------------------------------------------------------------------- #
def test_select_non_conflicting_drops_overlap():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian", prio=Priority.MUST, match=95)
    b = _sess("b", "Tuesday", 9, 30, 10, 30, "Venetian", prio=Priority.LOW, match=60)
    chosen = planning.select_non_conflicting([a, b], VENUES)
    ids = {s.id for s in chosen}
    assert "a" in ids and "b" not in ids


def test_select_skips_cancelled():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    a.status = SessionStatus.CANCELLED
    assert planning.select_non_conflicting([a], VENUES) == []


# --------------------------------------------------------------------------- #
# Travel legs / buffers
# --------------------------------------------------------------------------- #
def test_travel_legs_have_buffer():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = _sess("b", "Tuesday", 11, 0, 12, 0, "Caesars Forum")
    legs = planning.build_travel_legs([a, b], VENUES)
    assert len(legs) == 1
    assert legs[0].from_venue == "Venetian" and legs[0].to_venue == "Caesars Forum"
    assert legs[0].buffer_minutes >= 0


def test_same_venue_no_leg():
    a = _sess("a", "Tuesday", 9, 0, 10, 0, "Venetian")
    b = _sess("b", "Tuesday", 10, 30, 11, 0, "Venetian")
    assert planning.build_travel_legs([a, b], VENUES) == []


# --------------------------------------------------------------------------- #
# Capacity
# --------------------------------------------------------------------------- #
def test_capacity_overloaded():
    state = planning.assess_capacity(session_count=7, walking_km=9.0, venue_changes=4, break_minutes=10)
    assert state.value == "overloaded"


def test_capacity_sustainable():
    state = planning.assess_capacity(session_count=2, walking_km=2.0, venue_changes=1, break_minutes=60)
    assert state.value == "sustainable"


# --------------------------------------------------------------------------- #
# Flight recommendation logic
# --------------------------------------------------------------------------- #
def test_flight_prefers_early_arrival():
    prefs = TripPreferences()
    flights = tools.FLIGHTS.search_flights(prefs)
    first_session = datetime(2026, 12, 1, 9, 0)
    recs = planning.recommend_flights(flights, prefs, first_session)
    rec = next(r for r in recs if r.recommended)
    # Recommended flight must arrive before the first session with room to spare.
    assert rec.flight.arrive < first_session


# --------------------------------------------------------------------------- #
# Tools return structured data
# --------------------------------------------------------------------------- #
def test_search_sessions_tool():
    res = tools.search_sessions(["Agents"])
    assert "sessions" in res and len(res["sessions"]) > 0


def test_recommend_alternatives_tool():
    res = tools.recommend_alternatives("se-1")
    assert res["dropped_session_id"] == "se-1"
    assert res["recommended_alternative_id"] is not None
    assert len(res["alternatives"]) >= 1
    # Alternatives must protect the same learning topic (Agents).
    assert all(a["session"]["topic"] == "Agents" or a["match_score"] >= 70 for a in res["alternatives"])


def test_conflict_tool_on_demo_data():
    # se-2 (Caesars 10:30-11:30) and se-4 (MGM 11:00-12:00) overlap.
    res = tools.check_session_conflicts(["se-2", "se-4"])
    assert len(res["conflicts"]) == 1


# --------------------------------------------------------------------------- #
# End-to-end orchestration
# --------------------------------------------------------------------------- #
def test_orchestrate_plan_end_to_end():
    plan = navigator.orchestrate_plan(
        "I'm traveling from Chennai to Las Vegas. Focus on Generative AI and Agents, "
        "arrive one day early, stay near the venues, reasonable budget."
    )
    assert plan.trip.origin == "Chennai"
    assert "Agents" in plan.trip.learning_goal
    assert len(plan.flight_recommendations) > 0
    assert any(r.recommended for r in plan.flight_recommendations)
    assert len(plan.hotel_recommendations) > 0
    assert len(plan.sessions) > 0
    assert len(plan.daily_schedule) > 0
    assert plan.daily_schedule[0].day == "Arrival Day"
    assert len(plan.preparation_checklist) == 2
    assert 0 <= plan.scores.route_quality <= 100
    assert 0 <= plan.scores.journey_score <= 100
    assert len(plan.agent_activity) >= 5
    # Selected sessions must be conflict-free.
    assert planning.detect_conflicts(plan.sessions, VENUES) == []


def test_orchestrate_reroute():
    plan = navigator.orchestrate_plan("Focus on Agents and Bedrock")
    selected_ids = [s.id for s in plan.sessions]
    result = navigator.orchestrate_reroute("se-1", selected_ids, "Session is full")
    assert result.dropped_session_id == "se-1"
    assert len(result.alternatives) >= 1
    assert len(result.metrics) == 4
    assert len(result.agent_activity) >= 3


def test_parse_mission_extracts_topics_and_origin():
    prefs = navigator.parse_mission("From Bangalore, focus on serverless and security, arrive one day early")
    assert prefs.origin == "Bangalore"
    assert "Serverless" in prefs.topics
    assert "Security" in prefs.topics
    assert prefs.arrive_days_early == 1


# --------------------------------------------------------------------------- #
# AWS Strands framework wiring
# --------------------------------------------------------------------------- #
def test_strands_tools_are_decorated():
    """The 9 tools must be registered as real Strands tools (carry tool_name)."""
    from app.agent import tools as t
    if not t.HAVE_STRANDS:
        import pytest
        pytest.skip("strands-agents not installed in this environment")
    names = {getattr(fn, "tool_name", getattr(fn, "__name__", "")) for fn in t.ALL_TOOLS}
    for expected in [
        "search_flights", "search_hotels", "search_sessions",
        "check_session_conflicts", "estimate_travel_time", "build_daily_schedule",
        "generate_preparation_checklist", "recommend_alternatives",
    ]:
        assert expected in names


def test_strands_agent_builds_with_all_tools():
    from app.agent import strands_agent as sa
    if not sa.tools.HAVE_STRANDS:
        import pytest
        pytest.skip("strands-agents not installed")
    status = sa.agent_status()
    assert status["strands_installed"] is True
    assert status["agent_built"] is True
    assert len(status["tools_registered"]) >= 9
    assert "explain_session_types" in status["tools_registered"]
    assert "import_session_catalog" in status["tools_registered"]


def test_orchestrator_defaults_to_deterministic_without_creds(monkeypatch):
    """Without REROUTE_USE_STRANDS_MODEL, the deterministic tool pipeline runs."""
    from app.agent import strands_agent as sa
    monkeypatch.delenv("REROUTE_USE_STRANDS_MODEL", raising=False)
    assert sa.model_available() is False
    plan = navigator.orchestrate_plan("Focus on Agents and Bedrock")
    assert len(plan.sessions) > 0  # deterministic path still produces a full plan


# --------------------------------------------------------------------------- #
# Model registry (Amazon Nova / Claude) + voice
# --------------------------------------------------------------------------- #
def test_model_registry_includes_nova():
    from app.agent import strands_agent as sa
    keys = {m["key"] for m in sa.list_models()}
    assert {"nova-pro", "nova-lite", "nova-micro"}.issubset(keys)
    ids = {m["model_id"] for m in sa.list_models()}
    assert any("amazon.nova" in i for i in ids)


def test_default_model_is_nova():
    from app.agent import strands_agent as sa
    sa.select_model("nova-pro")
    active = sa.active_model()
    assert active["family"] == "nova"
    assert "nova" in active["model_id"]


def test_select_model_switches_and_rebuilds():
    from app.agent import strands_agent as sa
    a = sa.select_model("nova-lite")
    assert a["family"] == "nova"
    assert sa.DEFAULT_MODEL_ID == a["model_id"]
    # switch back so other tests see the default
    sa.select_model("nova-pro")


def test_voice_config_reports_provider_and_voices():
    from app import voice
    cfg = voice.voice_config()
    assert "provider" in cfg
    assert cfg["stt_provider"] == "browser-web-speech-api"
    assert len(cfg["voices"]) >= 3
    # Includes an Indian-English voice for attendees traveling from India.
    assert any(v["lang"] == "en-IN" for v in cfg["voices"])


def test_synthesize_returns_none_without_polly(monkeypatch):
    from app import voice
    monkeypatch.delenv("REROUTE_USE_POLLY", raising=False)
    assert voice.synthesize("hello") is None  # falls back to browser TTS


def test_spoken_summary_is_speakable():
    from app.api import spoken_summary
    plan = navigator.orchestrate_plan("Focus on Agents and Bedrock")
    text = spoken_summary(plan)
    assert plan.trip.learning_goal in text
    assert "journey score" in text.lower()
    assert len(text) > 40


# --------------------------------------------------------------------------- #
# Real session catalog provider
# --------------------------------------------------------------------------- #
def test_catalog_loads_sample_json():
    from app.providers.catalog_provider import load_catalog
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_catalog.json")
    sessions = load_catalog(path)
    assert len(sessions) == 4
    # Verified (real export) not demo.
    assert all(s.confidence.value == "verified" for s in sessions)
    # Topic derivation from title/track.
    by_id = {s.id: s for s in sessions}
    assert by_id["AIM301"].topic == "Agents"
    assert by_id["SEC302"].topic == "Generative AI"


def test_catalog_provider_uses_file_when_present():
    from app.providers.catalog_provider import CatalogSessionProvider
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_catalog.json")
    p = CatalogSessionProvider(path)
    assert p.source == "catalog"
    assert {s.id for s in p.search_sessions(["Agents"])} == {"AIM301", "AIM401", "AIM205"}
    assert p.get_session("AIM301") is not None


def test_catalog_provider_falls_back_to_demo(monkeypatch):
    from app.providers.catalog_provider import CatalogSessionProvider
    monkeypatch.delenv("REROUTE_SESSION_CATALOG", raising=False)
    p = CatalogSessionProvider(path="does-not-exist.json")
    assert p.source == "demo"
    # Demo catalog still returns its sessions.
    assert len(p.search_sessions(["Agents"])) > 0


def test_catalog_flexible_field_mapping():
    from app.providers.catalog_provider import _row_to_session
    row = {"name": "My Session", "start_time": "2026-12-01T09:00:00", "location": "Venetian"}
    s = _row_to_session(row, 0)
    assert s is not None
    assert s.title == "My Session"
    assert s.venue == "Venetian"
    assert s.day == "Tuesday"


# --------------------------------------------------------------------------- #
# Session types reference + paste import
# --------------------------------------------------------------------------- #
def test_explain_session_types_tool():
    from app.agent import tools as t
    res = t.explain_session_types()
    type_names = {x["type"] for x in res["session_types"]}
    assert {"Breakout", "Workshop", "Chalk Talk"}.issubset(type_names)
    levels = {x["level"] for x in res["content_levels"]}
    assert {"100", "200", "300", "400"} == levels
    # Workshops are hands-on and 120 min.
    ws = next(x for x in res["session_types"] if x["type"] == "Workshop")
    assert ws["hands_on"] is True and ws["duration_min"] == 120


def test_import_catalog_from_json_text():
    import json as _json
    from app.agent import tools as t
    txt = _json.dumps({"sessions": [
        {"code": "IMP1", "title": "Agents 101", "track": "AI/ML",
         "startTime": "2026-12-01T09:00:00", "venue": "Venetian"},
    ]})
    res = t.import_session_catalog(txt)
    assert res["imported"] == 1
    assert res["session_source"] == "catalog"
    assert t.SESSIONS.get_session("IMP1") is not None
    # (autouse fixture restores the demo catalog after this test)


def test_import_catalog_from_csv_text():
    from app.providers.catalog_provider import load_catalog_from_text
    csv_txt = "title,startTime,venue\nMy Talk,2026-12-02T10:00:00,MGM Grand\n"
    sessions = load_catalog_from_text(csv_txt, "csv")
    assert len(sessions) == 1
    assert sessions[0].title == "My Talk"
    assert sessions[0].venue == "MGM Grand"


# --------------------------------------------------------------------------- #
# re:Invent 2026 model: official links, venues/shuttle, learning modes, scores
# --------------------------------------------------------------------------- #
def test_official_links_present():
    from app.official_links import OFFICIAL_LINKS
    for key in ("eventCatalog", "keynotes", "securityFocus", "expo", "accessibility", "registration"):
        assert key in OFFICIAL_LINKS
        assert OFFICIAL_LINKS[key].startswith("https://")


def test_venue_travel_uses_shuttle_for_far_venues():
    v = DemoVenueProvider()
    # Venetian <-> MGM is far: shuttle, not walkable.
    km, minutes, shuttle = v.travel("Venetian", "MGM Grand")
    assert shuttle is True
    assert minutes < 40  # shuttle is faster than the 65-min walk
    # Wynn <-> Encore is walkable.
    _, _, shuttle2 = v.travel("Wynn", "Encore")
    assert shuttle2 is False


def test_session_enriched_with_mode_and_level():
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    ws = p.get_session("se-3")  # Workshop
    assert ws.learning_mode == "Build It Yourself"
    assert ws.hands_on is True
    assert ws.catalog_url and ws.catalog_url.startswith("https://")
    bo = p.get_session("se-1")  # Breakout
    assert bo.learning_mode == "Watch and Learn"
    assert bo.hands_on is False


def test_learning_mode_mix_sums_to_100():
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    sessions = p.search_sessions(["Agents", "Generative AI"])
    mix = planning.learning_mode_mix(sessions)
    assert abs(sum(mix.values()) - 100) <= 1  # rounding tolerance


def test_journey_score_has_multifactor_breakdown():
    plan = navigator.orchestrate_plan("Master production Agentic AI, focus on Agents and Bedrock")
    b = plan.scores.breakdown
    for factor in ("Goal alignment", "Coverage", "Hands-on", "Format balance", "Recovery", "Human capacity"):
        assert factor in b and 0 <= b[factor] <= 100
    assert plan.scores.learning_mode_mix
    # Journey Analyst agent participated.
    assert any(a.agent == "Journey Analyst" for a in plan.agent_activity)


def test_mode_balance_recommends_handson_for_implementation_goal():
    # A mostly-passive mix with an implementation goal should trigger advice.
    mix = {"Watch and Learn": 80, "Work Alongside Experts": 0, "Build It Yourself": 20, "Certification": 0}
    advice = planning.mode_balance_recommendation(mix, ["Agents", "production"])
    assert advice and "hands-on" in advice.lower()


# --------------------------------------------------------------------------- #
# Learning graph
# --------------------------------------------------------------------------- #
def test_learning_graph_states_and_gaps():
    from app.engine import learning_graph as lg
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    found = p.search_sessions(["Agents", "Generative AI", "Amazon Bedrock"])
    selected = planning.select_non_conflicting(found, VENUES)
    g = lg.build_learning_graph(["Agents"], selected, set())
    states = {n["id"]: n["state"] for n in g["nodes"]}
    # Agents is covered by the demo route -> in_progress or completed.
    assert states["Agents"] in ("in_progress", "completed")
    # A goal-path node with no session is a gap.
    assert g["gap_count"] >= 1
    assert len(g["edges"]) == len(lg.GRAPH_EDGES)
    # Off-path foundational topics are optional.
    assert states["Data"] == "optional"


def test_learning_graph_marks_attended_completed():
    from app.engine import learning_graph as lg
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    selected = p.search_sessions(["Agents"])
    attended = {selected[0].id}
    g = lg.build_learning_graph(["Agents"], selected, attended)
    # Agents node should now be completed (an attended session covers it).
    agents = next(n for n in g["nodes"] if n["id"] == "Agents")
    assert agents["state"] == "completed"


def test_learning_graph_goal_path_selection():
    from app.engine import learning_graph as lg
    g = lg.build_learning_graph(["Security"], [], set())
    on_path = {n["id"] for n in g["nodes"] if n["on_goal_path"]}
    assert "Security" in on_path and "Implementation" in on_path


# --------------------------------------------------------------------------- #
# Semantic session search
# --------------------------------------------------------------------------- #
def test_embedding_provider_local_fallback():
    from app.providers import embeddings
    p = embeddings.get_embedding_provider()
    # No AWS creds in test env -> local hash embedder.
    assert p.name == "local-hash"
    v = p.embed("production AI agents")
    assert isinstance(v, list) and len(v) > 0


def test_cosine_similarity_bounds():
    from app.providers.embeddings import cosine, LocalHashEmbeddingProvider
    p = LocalHashEmbeddingProvider()
    a = p.embed("build production agents workshop hands-on")
    b = p.embed("ship an agent to production with a builders lab")
    c = p.embed("networking reception dinner")
    # Related texts should score higher than unrelated.
    assert cosine(a, b) > cosine(a, c)


def test_semantic_search_ranks_handson_for_build_query():
    from app.engine import semantic
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    alls = p.search_sessions([])
    ranked = semantic.semantic_search("build and ship production AI agents hands-on", alls, top_k=3)
    top_ids = [s.id for s in ranked]
    # A workshop should surface in the top results for a hands-on build query.
    top_formats = {p.get_session(sid).format for sid in top_ids}
    assert "Workshop" in top_formats


def test_semantic_search_surfaces_security_session():
    from app.engine import semantic
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    alls = p.search_sessions([])
    ranked = semantic.semantic_search("secure my generative AI applications", alls, top_k=3)
    # The security session (se-7) should rank near the top.
    assert "se-7" in [s.id for s in ranked]


def test_search_sessions_semantic_tool():
    from app.agent import tools as t
    res = t.search_sessions_semantic("production agentic AI hands-on", top_k=5)
    assert "sessions" in res and len(res["sessions"]) > 0
    assert res["provider"] in ("local-hash", "bedrock-titan")
    # Scores should be sorted descending.
    scores = [s["match_score"] for s in res["sessions"]]
    assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------- #
# Scraper + MCP server
# --------------------------------------------------------------------------- #
def test_scraper_import_text():
    import json as _json
    from app import scraper
    txt = _json.dumps({"sessions": [
        {"code": "SCR1", "title": "Scraped agent session", "track": "AI/ML",
         "startTime": "2026-12-01T09:00:00", "venue": "The Venetian"},
    ]})
    res = scraper.load_from_text(txt)
    assert res.ok and len(res.sessions) == 1
    assert res.sessions[0].id == "SCR1"


def test_scraper_public_gated_note_without_playwright():
    from app import scraper
    if scraper._playwright_available():
        import pytest
        pytest.skip("Playwright installed; skipping the no-playwright path")
    res = scraper.scrape_public_url()
    assert res.ok is False
    assert "Playwright" in res.note


def test_scraper_harvest_finds_sessions_in_nested_json():
    from app import scraper
    data = {"page": {"widgets": [{"items": [
        {"title": "Nested session", "startTime": "2026-12-01T10:00:00", "venue": "Wynn"},
    ]}]}}
    rows = scraper._harvest(data)
    assert len(rows) == 1 and rows[0]["title"] == "Nested session"


def test_mcp_server_lists_all_tools():
    import asyncio
    from app import mcp_server
    tool_list = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tool_list}
    for expected in ("scrape_catalog", "search_sessions", "search_sessions_semantic",
                     "get_session", "list_venues", "estimate_travel", "official_links",
                     "catalog_status"):
        assert expected in names


def test_mcp_scrape_catalog_import_loads_source():
    import json as _json
    from app import mcp_server
    txt = _json.dumps({"sessions": [
        {"code": "MCPX", "title": "MCP session", "track": "AI/ML",
         "startTime": "2026-12-01T09:00:00", "venue": "The Venetian"},
    ]})
    res = mcp_server.scrape_catalog(mode="import", text=txt)
    assert res["ok"] and res["count"] == 1
    assert res["loaded_into_active_source"] == 1
    # restore demo for other tests
    from app.providers.catalog_provider import CatalogSessionProvider
    mcp_server._SESSIONS.load_sessions([]) if hasattr(mcp_server._SESSIONS, "load_sessions") else None


def test_mcp_estimate_travel_and_official_links():
    from app import mcp_server
    t = mcp_server.estimate_travel("The Venetian", "MGM Grand")
    assert t["shuttle"] is not None and t["walkable"] is False
    links = mcp_server.official_links()
    assert links["eventCatalog"].startswith("https://")


# --------------------------------------------------------------------------- #
# Real re:Invent 2026 catalog (scraped bundle) + API mapper
# --------------------------------------------------------------------------- #
def test_bundled_real_catalog_loads_and_is_large():
    import os
    from app.providers.catalog_provider import CatalogSessionProvider
    bundle = CatalogSessionProvider._BUNDLED
    if not os.path.exists(bundle):
        import pytest
        pytest.skip("bundled catalog not present")
    p = CatalogSessionProvider(bundle)
    assert p.source == "catalog"
    sessions = p.search_sessions([])
    assert len(sessions) > 1000  # the real catalog is ~1,500 sessions
    # Sessions are enriched with mode/level/hands_on and official catalog links.
    s = sessions[0]
    assert s.learning_mode in {
        "Watch and Learn", "Work Alongside Experts", "Build It Yourself", "Certification"
    }
    assert s.catalog_url and s.catalog_url.startswith("https://")


def test_aws_catalog_mapper_extracts_attributes():
    from app.aws_catalog import raw_items_to_sessions
    item = {
        "code": "AIM301", "title": "Build production agents", "type": "Workshop",
        "abstract": "hands on", "attributevalues": [
            {"attribute": "Level", "value": "300 - Advanced"},
            {"attribute": "Topic", "value": "Agents"},
        ],
    }
    sessions = raw_items_to_sessions([item])
    assert len(sessions) == 1
    s = sessions[0]
    assert s.format == "Workshop" and s.hands_on is True
    assert s.level == "300"
    assert s.topic == "Agents"


def test_selection_caps_sessions_per_day():
    from datetime import datetime
    sessions = []
    for i in range(8):  # 8 sessions same day, staggered, same venue (no conflict)
        sessions.append(Session(
            id=f"x{i}", title=f"S{i}", topic="Agents", format="Breakout",
            venue="The Venetian", room="R", day="Tuesday",
            start=datetime(2026, 12, 1, 8 + i, 0), end=datetime(2026, 12, 1, 8 + i, 45),
            priority=Priority.HIGH, status=SessionStatus.AVAILABLE, match_score=90,
        ))
    chosen = planning.select_non_conflicting(sessions, VENUES, max_per_day=4)
    assert len([s for s in chosen if s.day == "Tuesday"]) <= 4


# --------------------------------------------------------------------------- #
# MCP-backed session provider (reinvent2026-mcp integration)
# --------------------------------------------------------------------------- #
def test_mcp_provider_parses_tool_results(monkeypatch):
    """McpSessionProvider maps MCP tool JSON into enriched Session objects,
    using a stubbed _call so no subprocess is needed."""
    from app.providers.mcp_provider import McpSessionProvider

    fake = {
        "catalog_status": {"session_count": 1507, "source": "bundled"},
        "search_sessions": {"sessions": [
            {"id": "AIM301", "title": "Build production agents", "topic": "Agents",
             "format": "Workshop", "venue": "The Venetian", "day": "2026-12-01",
             "start": "2026-12-01T09:00:00", "level": "300"},
        ]},
        "semantic_search": {"sessions": [
            {"id": "AIM301", "title": "Build production agents", "topic": "Agents",
             "format": "Workshop", "start": "2026-12-01T09:00:00", "match_score": 92},
        ]},
        "get_session": {"id": "AIM301", "title": "Build production agents",
                        "topic": "Agents", "format": "Workshop",
                        "start": "2026-12-01T09:00:00"},
    }

    # Avoid real connection: stub _call and _connect.
    def fake_call(self, tool, args):
        return fake.get(tool, {})

    monkeypatch.setattr(McpSessionProvider, "_call", fake_call)
    monkeypatch.setattr(McpSessionProvider, "_connect", lambda self: setattr(self, "available", True))

    p = McpSessionProvider()
    assert p.source == "mcp"
    results = p.search_sessions(["Agents"])
    assert len(results) == 1
    s = results[0]
    assert s.format == "Workshop" and s.hands_on is True  # enriched
    assert s.learning_mode == "Build It Yourself"
    sem = p.semantic_search("build agents", 3)
    assert sem and sem[0].match_score == 92
    assert p.get_session("AIM301").title == "Build production agents"


def test_mcp_provider_status_shape(monkeypatch):
    from app.providers.mcp_provider import McpSessionProvider
    monkeypatch.setattr(McpSessionProvider, "_connect", lambda self: setattr(self, "available", False))
    p = McpSessionProvider()
    st = p.status()
    assert "available" in st and st["available"] is False


# --------------------------------------------------------------------------- #
# Catalog Explorer: facets + filter
# --------------------------------------------------------------------------- #
def test_catalog_facets_returns_dropdown_options():
    from app import api
    f = api.catalog_facets()
    assert f["total"] > 0
    # Levels and formats should be non-empty option lists for the dropdowns.
    assert f["levels"] and f["formats"] and f["venues"] and f["days"]
    assert isinstance(f["topics"], list)


def test_catalog_filter_by_format_and_text():
    from app import api
    # Demo catalog has Workshop sessions tagged Agents/GenAI.
    r = api.catalog_filter(format="Workshop", limit=50)
    assert r["total"] >= 1
    assert all(s["format"] == "Workshop" for s in r["sessions"])
    # Text filter narrows further.
    r2 = api.catalog_filter(text="agent", limit=50)
    assert all("agent" in (s["title"] + s["topic"]).lower() for s in r2["sessions"])


def test_catalog_filter_pagination():
    from app import api
    r1 = api.catalog_filter(limit=2, page=1)
    r2 = api.catalog_filter(limit=2, page=2)
    assert r1["limit"] == 2 and len(r1["sessions"]) <= 2
    if r1["total"] > 2:
        assert r1["sessions"] != r2["sessions"]  # different page


# --------------------------------------------------------------------------- #
# Add-session (Add to Route from Explore Catalog)
# --------------------------------------------------------------------------- #
def test_rebuild_plan_from_sessions_adds_and_scores():
    from app.agent import navigator
    # Start with one session, add another; plan should include both (if feasible)
    # and be fully assembled with scores + schedule.
    plan = navigator.rebuild_plan_from_sessions(["se-1", "se-5"])
    ids = {s.id for s in plan.sessions}
    assert "se-1" in ids or "se-5" in ids
    assert plan.daily_schedule and plan.daily_schedule[0].day == "Arrival Day"
    assert 0 <= plan.scores.journey_score <= 100
    # No conflicts remain in the final selection.
    assert planning.detect_conflicts(plan.sessions, VENUES) == []


def test_add_session_endpoint_dedupes():
    from app import api
    plan = api.add_session(api.AddSessionRequest(
        current_selected_ids=["se-1"], session_id="se-1", learning_goal="Agents"
    ))
    # Adding a session already present should not duplicate it.
    assert [s.id for s in plan.sessions].count("se-1") <= 1


# --------------------------------------------------------------------------- #
# RAG preparation advice (knowledge base of past experience)
# --------------------------------------------------------------------------- #
def test_knowledge_base_loads_seed_tips():
    from app.engine import knowledge
    kb = knowledge.KnowledgeBase()
    assert kb.loaded and kb.count() >= 10


def test_advise_retrieves_relevant_tips():
    from app.engine import knowledge
    adv = knowledge.advise("security focus and long-haul travel", top_k=3)
    assert adv["tips"] and len(adv["tips"]) <= 3
    # Top result should be security-related for a security query.
    joined = " ".join(t["text"].lower() + " ".join(t["tags"]) for t in adv["tips"])
    assert "security" in joined
    assert adv["commentary"]  # grounded commentary present


def test_advise_ranks_handson_for_learning_query():
    from app.engine import knowledge
    adv = knowledge.advise("avoid burnout, get hands-on workshops", top_k=3)
    tags = {tag for t in adv["tips"] for tag in t["tags"]}
    assert tags & {"balance", "capacity", "workshops", "burnout"}


def test_add_tips_at_runtime():
    from app.engine import knowledge
    kb = knowledge.KnowledgeBase()
    before = kb.count()
    kb.add_tips([{"text": "Bring a portable charger; sessions drain your phone.", "tags": ["prep", "power"]}])
    assert kb.count() == before + 1
    hit = kb.retrieve("phone battery charger", top_k=1)
    assert hit and "charger" in hit[0].text.lower()


def test_retrieve_tips_tool_and_endpoint():
    from app.agent import tools as t
    res = t.retrieve_tips("prepare for re:Invent from overseas", top_k=2)
    assert "tips" in res and res["knowledge_count"] >= 10
    from app import api
    adv = api.advice(api.AdviceRequest(mission="focus on agents, arrive early"))
    assert adv["tips"]


def test_plan_includes_rag_prep_tips():
    plan = navigator.orchestrate_plan("Master production Agentic AI, arrive one day early, security focus")
    # At least one recommendation should be a grounded prep tip.
    assert any(r.startswith("Prep tip:") for r in plan.recommendations)


# --------------------------------------------------------------------------- #
# Plan A / B / C generator
# --------------------------------------------------------------------------- #
def test_build_abc_returns_three_labeled_plans():
    from app.agent import navigator
    res = navigator.build_abc_plans("Master production Agentic AI, focus on Agents and Bedrock")
    plans = res["plans"]
    assert len(plans) == 3
    assert [p["key"] for p in plans] == ["A", "B", "C"]
    for p in plans:
        assert p["rationale"] and p["plan"]["sessions"]
        assert 0 <= p["summary"]["journey_score"] <= 100


def test_abc_plans_are_distinct():
    from app.agent import navigator
    res = navigator.build_abc_plans("Focus on Agents and Bedrock and Generative AI")
    a = {s["id"] for s in res["plans"][0]["plan"]["sessions"]}
    b = {s["id"] for s in res["plans"][1]["plan"]["sessions"]}
    c = res["plans"][2]["summary"]
    # Backup avoids A's picks -> largely different set.
    assert a != b
    # Low-risk should be lighter (fewer/equal venue changes than ideal).
    assert c["venue_changes"] <= res["plans"][0]["summary"]["venue_changes"]


def test_abc_plans_are_conflict_free():
    from app.agent import navigator
    from app.models import Session
    res = navigator.build_abc_plans("Focus on Agents")
    for p in res["plans"]:
        sessions = [Session(**s) for s in p["plan"]["sessions"]]
        assert planning.detect_conflicts(sessions, VENUES) == []


# --------------------------------------------------------------------------- #
# AWS services integration status
# --------------------------------------------------------------------------- #
def test_model_registry_has_latest_models():
    from app.agent import strands_agent as sa
    keys = {m["key"] for m in sa.list_models()}
    # Amazon models only.
    assert {"nova-premier", "nova-pro", "nova-lite", "nova-micro"} == keys
    assert all(m["family"] == "nova" for m in sa.list_models())


def test_aws_status_reports_all_services():
    from app import aws_status
    s = aws_status.aws_status()
    for svc in ("bedrock_agent", "bedrock_embeddings", "polly_tts", "session_source"):
        assert svc in s["services"]
        assert "toggle_env" in s["services"][svc]
    assert "any_aws_service_live" in s
    assert "boto3_installed" in s


def test_aws_status_endpoint():
    from app import api
    s = api.aws_status()
    assert s["services"]["bedrock_agent"]["toggle_env"] == "REROUTE_USE_STRANDS_MODEL=1"
    assert s["services"]["bedrock_embeddings"]["model"].startswith("amazon.titan")


# --------------------------------------------------------------------------- #
# Agent reasoning visibility (why kept / why dropped)
# --------------------------------------------------------------------------- #
def test_plan_sessions_have_why():
    plan = navigator.orchestrate_plan("Master production Agentic AI, focus on Agents and Bedrock")
    assert plan.sessions
    for s in plan.sessions:
        assert s.why  # every kept session explains itself
        assert "match to your goal" in s.why


def test_plan_reports_dropped_with_reasons():
    plan = navigator.orchestrate_plan("Focus on Agents and Bedrock and Generative AI")
    # Notable drops are surfaced (capped), each with a concrete reason.
    assert len(plan.dropped_sessions) <= 8
    if plan.dropped_sessions:
        d = plan.dropped_sessions[0]
        assert d.id and d.title and d.reason
        assert any(k in d.reason for k in ("Time overlap", "Tight transition", "sessions"))


def test_explain_selection_marks_handson():
    from app.providers.demo_providers import DemoSessionProvider
    p = DemoSessionProvider()
    found = p.search_sessions(["Agents", "Generative AI"])
    selected = planning.select_non_conflicting(found, VENUES, ["Agents"])
    kept, dropped = planning.explain_selection(selected, found, VENUES, ["Agents"])
    ws = next((s for s in kept if s.hands_on), None)
    if ws:
        assert "hands-on" in ws.why
