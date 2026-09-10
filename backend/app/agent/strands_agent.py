"""Real AWS Strands Agents integration for Re:Route AI.

This module makes the Strands framework the actual orchestrator of record, not a
decoration. It builds a `strands.Agent` backed by a Bedrock model and lets the
LLM drive the tool-calling loop over the same `@tool` functions used everywhere
else. Two model-driven entry points are provided:

  * run_agent_plan(mission)        -> the agent plans the whole trip
  * run_agent_reroute(...)         -> the agent recovers a broken route

Both return the structured Pydantic models via Strands' `structured_output`, so
the frontend contract is unchanged.

If no model / AWS credentials are configured (common in local/hackathon dev),
the callers in navigator.py fall back to the deterministic pipeline that invokes
the identical tools. `agent_status()` reports which path is live so the UI can
show it honestly.
"""
from __future__ import annotations

import os

from app.agent import tools
from app.models import Plan, RerouteResult

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# --------------------------------------------------------------------------- #
# Model registry — selectable Bedrock models, including Amazon Nova.
# key -> {label, model_id, family}
# --------------------------------------------------------------------------- #
# Amazon models only (Bedrock Nova family). Native to AWS, cost-effective, and
# the simplest permission/deploy path for a serverless (Lambda) hackathon build.
MODEL_REGISTRY: dict[str, dict[str, str]] = {
    "nova-premier": {
        "label": "Amazon Nova Premier",
        "model_id": "us.amazon.nova-premier-v1:0",
        "family": "nova",
    },
    "nova-pro": {
        "label": "Amazon Nova Pro",
        "model_id": "us.amazon.nova-pro-v1:0",
        "family": "nova",
    },
    "nova-lite": {
        "label": "Amazon Nova Lite",
        "model_id": "us.amazon.nova-lite-v1:0",
        "family": "nova",
    },
    "nova-micro": {
        "label": "Amazon Nova Micro",
        "model_id": "us.amazon.nova-micro-v1:0",
        "family": "nova",
    },
}

# Default to Amazon Nova Pro (multi-purpose, cost-effective, native to AWS).
DEFAULT_MODEL_KEY = os.getenv("REROUTE_MODEL", "nova-pro")


def _resolve_model_id(model_key: str | None) -> tuple[str, str]:
    """Return (model_key, model_id). Accepts a registry key or a raw model id."""
    if model_key and model_key in MODEL_REGISTRY:
        return model_key, MODEL_REGISTRY[model_key]["model_id"]
    # Allow a raw override id (e.g. REROUTE_BEDROCK_MODEL) or unknown key.
    raw = os.getenv("REROUTE_BEDROCK_MODEL")
    if raw:
        return "custom", raw
    if model_key:  # treat as a raw id
        return "custom", model_key
    fallback = DEFAULT_MODEL_KEY if DEFAULT_MODEL_KEY in MODEL_REGISTRY else "nova-pro"
    return fallback, MODEL_REGISTRY[fallback]["model_id"]


# Active selection (can be changed at runtime via select_model()).
_active_model_key, DEFAULT_MODEL_ID = _resolve_model_id(DEFAULT_MODEL_KEY)

SYSTEM_PROMPT = """You are the Navigator for Re:Route AI, an autonomous multi-agent
assistant for AWS re:Invent attendees. Protect the attendee's LEARNING GOAL — do
NOT maximize the number of sessions. The destination stays the same; the route can
change.

You have specialized tools. Use them yourself to reason through the plan:
1. search_sessions — find sessions matching the learning topics.
2. check_session_conflicts — detect time overlaps and infeasible venue transitions.
3. estimate_travel_time — check walking/shuttle time between venues.
4. build_daily_schedule — assemble a realistic daily plan with breaks and buffers.
5. search_flights / search_hotels — recommend travel that gets the attendee to their
   first session on time and within budget.
6. generate_preparation_checklist — produce a personalized checklist.
7. recommend_alternatives — when a session is full/cancelled, find same-topic fallbacks.

Plan for a real human: respect walking limits, buffers between venues, breaks and
lunch. Never claim real-time availability — data is simulated (DEMO). Keep any
explanations short and decision-focused.
"""

_agent = None
_agent_error: str | None = None


def _load_mcp_tools() -> list:
    """Attach the reinvent-2026 MCP server's tools to the agent when enabled.

    Set REROUTE_ATTACH_MCP=1 to have the Strands agent connect to the MCP server
    over stdio and expose its tools (scrape_catalog, search_sessions, …) to the
    model alongside the native tools. Fails soft: returns [] if unavailable.
    """
    if os.getenv("REROUTE_ATTACH_MCP", "").lower() not in ("1", "true", "yes"):
        return []
    try:  # pragma: no cover - requires mcp client + subprocess at runtime
        from mcp import StdioServerParameters
        from strands.tools.mcp import MCPClient

        # Prefer the standalone, publishable reinvent2026-mcp package; fall back
        # to the in-repo server. Configure with REROUTE_MCP_CMD/REROUTE_MCP_ARGS.
        cmd = os.getenv("REROUTE_MCP_CMD", "python")
        args_env = os.getenv("REROUTE_MCP_ARGS")
        args = args_env.split() if args_env else ["-m", "app.mcp_server"]
        client = MCPClient(lambda: StdioServerParameters(command=cmd, args=args))
        client.start()
        return client.list_tools_sync()
    except Exception:
        return []


def _build_agent():
    """Construct the Strands Agent with the active Bedrock model. Returns (agent, error)."""
    try:
        from strands import Agent
        from strands.models import BedrockModel

        model = BedrockModel(model_id=DEFAULT_MODEL_ID, region_name=AWS_REGION)
        all_tools = list(tools.ALL_TOOLS) + _load_mcp_tools()
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=all_tools,
            name="Navigator",
            description="Re:Route AI orchestrator for AWS re:Invent planning.",
        )
        return agent, None
    except Exception as exc:  # pragma: no cover - depends on env/creds
        return None, f"{type(exc).__name__}: {exc}"


def get_agent():
    """Lazily build and cache the Strands Agent."""
    global _agent, _agent_error
    if _agent is None and _agent_error is None:
        _agent, _agent_error = _build_agent()
    return _agent


def select_model(model_key: str) -> dict:
    """Switch the active Bedrock model at runtime and rebuild the agent."""
    global _active_model_key, DEFAULT_MODEL_ID, _agent, _agent_error
    _active_model_key, DEFAULT_MODEL_ID = _resolve_model_id(model_key)
    _agent = None
    _agent_error = None  # force rebuild on next get_agent()
    return active_model()


def active_model() -> dict:
    reg = MODEL_REGISTRY.get(_active_model_key, {})
    return {
        "key": _active_model_key,
        "model_id": DEFAULT_MODEL_ID,
        "label": reg.get("label", DEFAULT_MODEL_ID),
        "family": reg.get("family", "custom"),
    }


def list_models() -> list[dict]:
    return [
        {"key": k, "label": v["label"], "model_id": v["model_id"], "family": v["family"]}
        for k, v in MODEL_REGISTRY.items()
    ]


def agent_status() -> dict:
    """Report the live orchestration path for the UI/health endpoint."""
    agent = get_agent()
    return {
        "strands_installed": tools.HAVE_STRANDS,
        "active_model": active_model(),
        "available_models": list_models(),
        "model_id": DEFAULT_MODEL_ID,
        "region": AWS_REGION,
        "tools_registered": [getattr(t, "tool_name", getattr(t, "__name__", "?")) for t in tools.ALL_TOOLS],
        "agent_built": agent is not None,
        "agent_error": _agent_error,
    }


def model_available() -> bool:
    """True only if a Strands Agent with a working model was constructed AND we
    can actually invoke it (credentials present). We treat build success +
    explicit opt-in env as the gate to avoid failing calls in credential-less dev."""
    if os.getenv("REROUTE_USE_STRANDS_MODEL", "").lower() not in ("1", "true", "yes"):
        return False
    return get_agent() is not None


# --------------------------------------------------------------------------- #
# Model-driven entry points (used only when model_available()).
# --------------------------------------------------------------------------- #
def run_agent_plan(mission: str) -> Plan:
    """Let the Strands agent plan the trip and return a structured Plan.

    Uses Strands `structured_output` so the LLM's tool-driven reasoning is
    coerced into our Pydantic contract.
    """
    agent = get_agent()
    prompt = (
        f"Create a complete re:Invent preparation plan for this attendee:\n\n"
        f'"{mission}"\n\n'
        "Use your tools to find sessions, resolve conflicts, check venue "
        "transitions, build a daily schedule, recommend a flight and hotel, and "
        "produce a preparation checklist. Then return the full structured plan."
    )
    return agent.structured_output(Plan, prompt)


def run_agent_reroute(dropped_session_id: str, current_selected_ids: list[str], reason: str) -> RerouteResult:
    agent = get_agent()
    prompt = (
        f"The session '{dropped_session_id}' is no longer available ({reason}). "
        f"The current route is {current_selected_ids}. Use recommend_alternatives "
        "and estimate_travel_time to find the best same-topic replacement that "
        "protects the learning goal, and return the structured reroute result with "
        "a before/after comparison."
    )
    return agent.structured_output(RerouteResult, prompt)
