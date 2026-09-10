"""Learning graph.

A directed dependency graph over re:Invent learning topics. Given the user's
goal and their selected sessions, each node gets a state:

  completed     — the user has attended a session covering this topic
  in_progress   — a session covering this topic is on the route (not yet attended)
  recommended   — on the goal path and a session exists to fill it
  gap           — on the goal path but no session covers it (the Navigator flags it)
  optional      — adjacent/foundational topic, not central to this goal

The Navigator prioritizes sessions that close important gaps.
"""
from __future__ import annotations

from app.models import Session

# Canonical topic dependency chain (foundational -> advanced).
GRAPH_EDGES: list[tuple[str, str]] = [
    ("Generative AI", "Amazon Bedrock"),
    ("Amazon Bedrock", "Agents"),
    ("Agents", "AgentCore"),
    ("AgentCore", "Production Architecture"),
    ("Production Architecture", "Security"),
    ("Security", "Implementation"),
    # side paths
    ("Serverless", "Production Architecture"),
    ("Data", "Amazon Bedrock"),
]

NODES: list[str] = [
    "Generative AI", "Amazon Bedrock", "Agents", "AgentCore",
    "Production Architecture", "Security", "Implementation",
    "Serverless", "Data",
]

# Which nodes are "on the goal path" for a given set of goal topics.
_GOAL_PATHS: dict[str, list[str]] = {
    "agents": ["Generative AI", "Amazon Bedrock", "Agents", "AgentCore",
               "Production Architecture", "Implementation"],
    "generative ai": ["Generative AI", "Amazon Bedrock", "Agents", "Production Architecture"],
    "amazon bedrock": ["Generative AI", "Amazon Bedrock", "Agents", "AgentCore"],
    "security": ["Production Architecture", "Security", "Implementation"],
    "serverless": ["Serverless", "Production Architecture", "Implementation"],
    "data": ["Data", "Amazon Bedrock", "Production Architecture"],
}


def _goal_nodes(goal_topics: list[str]) -> set[str]:
    on_path: set[str] = set()
    for t in goal_topics or ["Agents"]:
        on_path.update(_GOAL_PATHS.get(t.strip().lower(), []))
    if not on_path:
        on_path = set(_GOAL_PATHS["agents"])
    return on_path


def _node_matches_session(node: str, s: Session) -> bool:
    text = f"{s.topic} {s.title}".lower()
    return node.lower() in text


def build_learning_graph(
    goal_topics: list[str],
    selected: list[Session],
    attended_ids: set[str] | None = None,
) -> dict:
    """Return {nodes:[{id,label,state,gap_fill_session_ids}], edges:[[from,to]]}."""
    attended_ids = attended_ids or set()
    on_path = _goal_nodes(goal_topics)

    attended = [s for s in selected if s.id in attended_ids]
    planned = [s for s in selected if s.id not in attended_ids]

    nodes = []
    gap_count = 0
    for node in NODES:
        covered_attended = any(_node_matches_session(node, s) for s in attended)
        covered_planned = [s for s in planned if _node_matches_session(node, s)]
        on_goal = node in on_path

        if covered_attended:
            state = "completed"
        elif covered_planned:
            state = "in_progress"
        elif on_goal:
            # No session covers a goal-path node.
            # If an available session could fill it, it's "recommended"; else a "gap".
            fillers = [s for s in selected if _node_matches_session(node, s)]
            state = "recommended" if fillers else "gap"
            if state == "gap":
                gap_count += 1
        else:
            state = "optional"

        nodes.append({
            "id": node,
            "label": node,
            "state": state,
            "on_goal_path": on_goal,
            "session_ids": [s.id for s in covered_planned],
        })

    return {
        "nodes": nodes,
        "edges": [list(e) for e in GRAPH_EDGES],
        "gap_count": gap_count,
        "goal_path": sorted(on_path),
    }
