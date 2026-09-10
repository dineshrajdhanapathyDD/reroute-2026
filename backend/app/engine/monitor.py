"""Autonomous background monitor — the "runs quietly, pings you only on a real
decision" core of Re:Route AI.

Most of the app is the planner. This module is the part that keeps working after
the plan is built: it watches the attendee's selected sessions and, on each scan
tick (a cron/EventBridge schedule in production, or the /api/monitor/scan
endpoint in the demo), autonomously re-checks the route against changing
conditions:

  * a selected session became FULL or CANCELLED
  * a session now has only a repeat/standby slot
  * a venue transition between two kept sessions became infeasible (too tight)

When it finds something that needs a HUMAN choice, it doesn't silently reshuffle
— it opens a *decision* with the problem, the impact, and pre-analyzed
recommended options (via the same recovery engine used by /api/reroute). The
decision sits dormant until the human approves or dismisses it. Nothing surfaces
when the route is healthy; that's the point.

State is a simple in-memory store (one watched plan for the demo). In production
this would be per-user and persisted; the scan logic is unchanged.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.agent import tools
from app.engine import planning
from app.models import SessionStatus

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
@dataclass
class Decision:
    id: str
    kind: str  # "session_full" | "session_cancelled" | "tight_transition"
    severity: str  # "high" | "medium"
    session_id: str
    title: str
    summary: str  # plain-language: what happened + why it needs you
    options: list[dict] = field(default_factory=list)  # recommended alternatives
    recommended_option_id: str | None = None
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # "pending" | "resolved" | "dismissed"
    resolution: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "session_id": self.session_id,
            "title": self.title,
            "summary": self.summary,
            "options": self.options,
            "recommended_option_id": self.recommended_option_id,
            "created_at": self.created_at,
            "status": self.status,
            "resolution": self.resolution,
        }


@dataclass
class WatchState:
    watching: bool = False
    learning_goal: str = ""
    selected_ids: list[str] = field(default_factory=list)
    decisions: dict[str, Decision] = field(default_factory=dict)
    last_scan_at: float = 0.0
    scan_count: int = 0
    # Which (session_id, kind) we've already raised, so a repeated scan doesn't
    # open duplicate decisions for the same unchanged problem.
    _seen: set = field(default_factory=set)
    # Status of each watched session at the moment we started watching. We only
    # raise a decision when a session degrades AFTER this baseline — a true
    # "something changed while running in the background" signal, not a
    # pre-existing condition.
    _baseline: dict = field(default_factory=dict)


_STATE = WatchState()


def watch(selected_ids: list[str], learning_goal: str = "") -> dict:
    """Start (or update) watching a plan. Snapshots current statuses as the
    baseline and resets prior decisions for a clean run."""
    _STATE.watching = True
    _STATE.learning_goal = learning_goal
    _STATE.selected_ids = list(selected_ids)
    _STATE.decisions = {}
    _STATE._seen = set()
    _STATE._baseline = {}
    for sid in selected_ids:
        s = tools.SESSIONS.get_session(sid)
        _STATE._baseline[sid] = s.status if s else None
    # Baseline conflicts: any tight transition that already exists at watch time
    # is part of the accepted plan, not a new problem to ping about.
    kept0 = [s for sid in selected_ids if (s := tools.SESSIONS.get_session(sid))]
    for c in planning.detect_conflicts(kept0, tools.VENUES):
        cid0 = getattr(c, "session_a_id", None) or getattr(c, "first_session_id", "")
        _STATE._seen.add((cid0 or getattr(c, "description", ""), "tight_transition"))
    _STATE.last_scan_at = 0.0
    _STATE.scan_count = 0
    return status()


def stop() -> dict:
    _STATE.watching = False
    return status()


# --------------------------------------------------------------------------- #
# The autonomous scan — the background tick.
# --------------------------------------------------------------------------- #
def scan() -> dict:
    """Run one monitoring pass. Returns the decisions that are newly raised this
    scan (empty when the route is healthy — the normal, quiet case)."""
    if not _STATE.watching:
        return {"watching": False, "new_decisions": [], "checked": 0}

    _STATE.scan_count += 1
    _STATE.last_scan_at = time.time()
    new: list[Decision] = []

    kept = [s for sid in _STATE.selected_ids if (s := tools.SESSIONS.get_session(sid))]

    # 1) Availability problems on kept sessions — only when the status DEGRADED
    #    from the baseline we captured at watch() time.
    _OK = {SessionStatus.AVAILABLE, SessionStatus.LIMITED, SessionStatus.RESERVED,
           SessionStatus.REPEAT_AVAILABLE, SessionStatus.RECORDING_AVAILABLE}
    for s in kept:
        baseline = _STATE._baseline.get(s.id)
        # If it was already problematic when we started watching, it's not a
        # change we should ping about.
        if baseline is not None and baseline not in _OK:
            continue
        problem = None
        if s.status == SessionStatus.CANCELLED:
            problem = ("session_cancelled", "high",
                       f"'{s.title}' was cancelled. It's on your route, so your "
                       "learning goal now has a gap that needs your call.")
        elif s.status == SessionStatus.FULL:
            problem = ("session_full", "high",
                       f"'{s.title}' just filled up. You can't attend as planned — "
                       "pick a replacement to protect your goal.")
        elif s.status == SessionStatus.STANDBY:
            problem = ("session_full", "medium",
                       f"'{s.title}' moved to standby. It may not work out — worth "
                       "lining up a backup.")
        if not problem:
            continue
        kind, severity, summary = problem
        key = (s.id, kind)
        if key in _STATE._seen:
            continue
        _STATE._seen.add(key)
        d = _build_reroute_decision(s.id, s.title, kind, severity, summary)
        _STATE.decisions[d.id] = d
        new.append(d)

    # 2) Newly infeasible venue transitions between kept sessions.
    conflicts = planning.detect_conflicts(
        [s for s in kept if s.status not in (SessionStatus.CANCELLED, SessionStatus.FULL)],
        tools.VENUES,
    )
    for c in conflicts:
        cid = getattr(c, "session_a_id", None) or getattr(c, "first_session_id", "")
        title_bits = getattr(c, "description", None) or getattr(c, "recommendation", "Tight transition")
        key = (cid or title_bits, "tight_transition")
        if not cid or key in _STATE._seen:
            continue
        _STATE._seen.add(key)
        sess = tools.SESSIONS.get_session(cid)
        d = _build_reroute_decision(
            cid, sess.title if sess else "Session", "tight_transition", "medium",
            f"Two of your sessions now have a transition that's too tight to make "
            f"comfortably. {title_bits}",
        )
        _STATE.decisions[d.id] = d
        new.append(d)

    return {
        "watching": True,
        "scan_count": _STATE.scan_count,
        "checked": len(kept),
        "new_decisions": [d.to_dict() for d in new],
        "pending": len([d for d in _STATE.decisions.values() if d.status == "pending"]),
    }


def _build_reroute_decision(session_id: str, title: str, kind: str, severity: str, summary: str) -> Decision:
    """Pre-analyze the fix so the ping already carries recommended options."""
    alt = tools.recommend_alternatives(session_id)
    options = []
    for a in alt.get("alternatives", [])[:3]:
        s = a.get("session", {})
        options.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "note": a.get("note", ""),
            "match_score": a.get("match_score", 0),
            "venue": s.get("venue"),
            "day": s.get("day"),
        })
    return Decision(
        id=f"dec-{uuid.uuid4().hex[:8]}",
        kind=kind,
        severity=severity,
        session_id=session_id,
        title=title,
        summary=summary,
        options=options,
        recommended_option_id=alt.get("recommended_alternative_id"),
    )


# --------------------------------------------------------------------------- #
# Human-in-the-loop resolution.
# --------------------------------------------------------------------------- #
def resolve(decision_id: str, action: str, chosen_option_id: str | None = None) -> dict:
    """Approve (swap in the chosen/recommended alternative) or dismiss a decision."""
    d = _STATE.decisions.get(decision_id)
    if not d:
        return {"error": "decision_not_found"}
    if action == "dismiss":
        d.status = "dismissed"
        d.resolution = "Dismissed by user"
        return {"decision": d.to_dict(), "selected_ids": _STATE.selected_ids}

    # approve: apply the swap to the watched plan.
    new_id = chosen_option_id or d.recommended_option_id
    if new_id:
        _STATE.selected_ids = [sid for sid in _STATE.selected_ids if sid != d.session_id]
        if new_id not in _STATE.selected_ids:
            _STATE.selected_ids.append(new_id)
    d.status = "resolved"
    chosen = next((o for o in d.options if o["id"] == new_id), None)
    d.resolution = f"Swapped to {chosen['title']}" if chosen else "Removed from route"
    return {"decision": d.to_dict(), "selected_ids": _STATE.selected_ids}


def status() -> dict:
    pending = [d.to_dict() for d in _STATE.decisions.values() if d.status == "pending"]
    history = [d.to_dict() for d in _STATE.decisions.values() if d.status != "pending"]
    pending.sort(key=lambda x: (x["severity"] != "high", -x["created_at"]))
    return {
        "watching": _STATE.watching,
        "learning_goal": _STATE.learning_goal,
        "watched_sessions": len(_STATE.selected_ids),
        "selected_ids": _STATE.selected_ids,
        "scan_count": _STATE.scan_count,
        "last_scan_at": _STATE.last_scan_at,
        "pending_decisions": pending,
        "resolved_decisions": history,
        "healthy": len(pending) == 0,
    }
