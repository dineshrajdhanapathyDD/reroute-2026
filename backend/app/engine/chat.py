"""Conversational entry point for Re:Route AI.

A newcomer-friendly chat handler. It reads a free-text message, figures out what
the person is trying to do (say hello, ask what re:Invent is, get preparation
advice, find sessions, or build a route), and answers in plain language. It
reuses the same engine capabilities the rest of the app uses — RAG advice,
semantic session search and the planning pipeline — so replies are grounded, not
invented.

When a Bedrock model is configured (REROUTE_USE_STRANDS_MODEL=1) the reply text
is phrased by the model; otherwise a deterministic, friendly template is used so
the demo always works. Either way the underlying data comes from the real tools.

The response is intentionally simple for the UI:
  {
    reply:        str,              # what the assistant says
    intent:       str,              # detected intent (for debugging/telemetry)
    suggestions:  [str],            # follow-up chips a newcomer can tap
    data: {                         # optional structured payload the UI can render
      kind: "plan" | "sessions" | "tips" | None,
      ...                           # shape depends on kind
    }
  }
"""
from __future__ import annotations

import re

from app.agent import navigator
from app.engine import knowledge

# --------------------------------------------------------------------------- #
# Intent detection — lightweight and deterministic.
# --------------------------------------------------------------------------- #
_GREETING = re.compile(r"\b(hi|hey|hello|yo|howdy|good (morning|afternoon|evening))\b", re.I)
_THANKS = re.compile(r"\b(thanks|thank you|thx|appreciate|cheers)\b", re.I)
_HELP = re.compile(r"\b(help|what can you do|how (do|does)|get started|new here|first time|newcomer|beginner|guide me|where do i start)\b", re.I)
_WHAT_IS = re.compile(r"\b(what is|what's|explain|tell me about)\b.*\b(re:?invent|reinvent|this|re:route|reroute)\b", re.I)
_ADVICE = re.compile(r"\b(tip|tips|advice|prepare|preparation|pack|packing|survive|first[- ]?time|shoes|water|badge|reserve|reservation|book)\b", re.I)
_FIND = re.compile(r"\b(find|show|search|list|any|which)\b.*\b(session|sessions|talk|talks|workshop|workshops|chalk)\b", re.I)
_PLAN_ABC = re.compile(r"\b(plan ?a|plan ?b|plan ?c|a ?/ ?b ?/ ?c|abc|three (plans|routes|options)|3 (plans|routes|options)|backup plan|compare (plans|routes|options)|options|alternatives)\b", re.I)
_PLAN = re.compile(r"\b(plan|build|create|itinerary|route|schedule|organi[sz]e|agenda)\b", re.I)

# Reused from the navigator's topic parser so chat and planning agree on topics.
_TOPIC_KEYWORDS = navigator._TOPIC_KEYWORDS  # noqa: SLF001


def _topics_in(text: str) -> list[str]:
    t = (text or "").lower()
    return [name for name, kws in _TOPIC_KEYWORDS.items() if any(k in t for k in kws)]


def detect_intent(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "greeting"
    if _WHAT_IS.search(t):
        return "explain"
    if _PLAN_ABC.search(t):
        return "plan_abc"
    if _PLAN.search(t):
        return "plan"
    if _FIND.search(t):
        return "find_sessions"
    if _ADVICE.search(t):
        return "advice"
    if _HELP.search(t):
        return "help"
    if _THANKS.search(t):
        return "thanks"
    if _GREETING.search(t):
        return "greeting"
    # If the message names a learning topic, treat it as a plan request.
    if _topics_in(t):
        return "plan"
    return "help"


# --------------------------------------------------------------------------- #
# Static, newcomer-friendly copy.
# --------------------------------------------------------------------------- #
_WELCOME = (
    "Hi! I'm your Re:Route AI navigator for AWS re:Invent. I help you turn a "
    "learning goal into a realistic, walkable plan — and I re-route you when a "
    "session fills up. Tell me what you want to get out of the week."
)

_EXPLAIN = (
    "AWS re:Invent is AWS's biggest yearly learning conference in Las Vegas — "
    "thousands of sessions across several venues over a week. It's easy to over-book "
    "and burn out. I protect your learning goal instead of your session count: I pick "
    "sessions that match what you want to learn, keep the walking and timing sane, and "
    "swap in alternatives when plans change."
)

_HELP_TEXT = (
    "Here's how we can work together:\n"
    "• Tell me a goal — e.g. \"I want to get production-ready with AI agents\" — and I'll build a route.\n"
    "• Ask for sessions on a topic — \"find Bedrock workshops\".\n"
    "• Ask for prep advice — \"what should a first-timer know?\".\n"
    "What would you like to start with?"
)

_DEFAULT_SUGGESTIONS = [
    "I'm new — where do I start?",
    "Build me a plan for learning GenAI",
    "Find hands-on Bedrock sessions",
    "First-timer tips",
]


# --------------------------------------------------------------------------- #
# Handler
# --------------------------------------------------------------------------- #
def chat(message: str, history: list[dict] | None = None) -> dict:
    intent = detect_intent(message)

    if intent == "greeting":
        return _reply(_WELCOME, intent, _DEFAULT_SUGGESTIONS)

    if intent == "thanks":
        return _reply(
            "Anytime. Want me to turn any of this into a day-by-day plan?",
            intent,
            ["Build me a plan", "Find more sessions", "First-timer tips"],
        )

    if intent == "explain":
        return _reply(
            _EXPLAIN, intent,
            ["Build me a plan", "What should a first-timer know?", "Find GenAI sessions"],
        )

    if intent == "help":
        return _reply(
            _HELP_TEXT, intent, _DEFAULT_SUGGESTIONS,
        )

    if intent == "advice":
        return _advice_reply(message)

    if intent == "find_sessions":
        return _sessions_reply(message)

    if intent == "plan_abc":
        return _plan_abc_reply(message)

    if intent == "plan":
        return _plan_reply(message)

    return _reply(_HELP_TEXT, "help", _DEFAULT_SUGGESTIONS)


def _advice_reply(message: str) -> dict:
    adv = knowledge.advise(message or "prepare for AWS re:Invent", top_k=3)
    tips = adv.get("tips", [])
    lead = adv.get("commentary", "")
    if tips:
        bullets = "\n".join(f"• {t['text']}" for t in tips)
        reply = f"{lead}\n\n{bullets}"
    else:
        reply = (
            "I don't have preparation tips loaded yet, but the classics: comfortable "
            "shoes, reserve popular sessions early, and leave buffer time to walk "
            "between venues."
        )
    return _reply(
        reply, "advice",
        ["Build me a plan", "Find sessions on a topic", "How much walking is there?"],
        data={"kind": "tips", "tips": tips},
    )


def _sessions_reply(message: str) -> dict:
    topics = _topics_in(message)
    search_topics = topics or ["Generative AI", "Agents"]
    res = tools_search(search_topics)
    sessions = res[:6]
    if sessions:
        names = topics_label(topics)
        listed = "\n".join(
            f"• {s['title']} — {s.get('format', 'Session')} · {s.get('level', '')}".strip()
            for s in sessions
        )
        reply = (
            f"Here are some {names} sessions I found "
            f"({len(res)} total match your topic):\n\n{listed}\n\n"
            "Want me to build these into a conflict-free daily plan?"
        )
    else:
        reply = (
            "I couldn't find sessions for that topic. Try a broader one like "
            "\"Generative AI\", \"Serverless\", or \"Security\"."
        )
    return _reply(
        reply, "find_sessions",
        ["Build a plan from these", "Show different topic", "First-timer tips"],
        data={"kind": "sessions", "sessions": sessions},
    )


def _plan_reply(message: str) -> dict:
    # Use the deterministic, tool-driven pipeline for chat: it always returns a
    # populated route quickly (real catalog + real engine), which keeps the
    # newcomer conversation responsive. The heavier model-driven planner remains
    # available on the dedicated /api/plan endpoint.
    plan = navigator._deterministic_plan(message)  # noqa: SLF001
    data = plan.model_dump(mode="json")
    n = len(plan.sessions)
    goal = plan.trip.learning_goal or "your goal"
    score = plan.scores.journey_score if plan.scores else 0
    reply = (
        f"Done — I built a route for {goal}. I picked {n} sessions that fit "
        f"together without conflicts and kept the walking realistic "
        f"(journey score {score}%). Open the plan to see the day-by-day schedule, "
        "or tell me what to change."
    )
    return _reply(
        reply, "plan",
        ["Give me Plan A / B / C options", "Make it more hands-on", "What if a session is full?"],
        data={"kind": "plan", "plan": data},
    )


def _plan_abc_reply(message: str) -> dict:
    """Three routes for one goal: A (ideal), B (backup), C (low-risk)."""
    res = navigator.build_abc_plans(message)
    plans = res.get("plans", [])
    goal = res.get("goal") or "your goal"
    if plans:
        lines = []
        for p in plans:
            s = p.get("summary", {})
            lines.append(
                f"• {p['label']} — {s.get('sessions', 0)} sessions · "
                f"journey {s.get('journey_score', 0)}% · {s.get('walking_km', 0)} km walking"
            )
        listed = "\n".join(lines)
        reply = (
            f"Here are three routes for {goal} — always have a backup:\n\n{listed}\n\n"
            "Plan A is your ideal picks, Plan B is the route you switch to when top "
            "sessions fill up, and Plan C keeps venue hops and burnout low. Open the "
            "comparison to pick one."
        )
    else:
        reply = (
            "I couldn't build the three plans just now. Tell me a learning goal like "
            "\"production-ready AI agents\" and I'll try again."
        )
    return _reply(
        reply, "plan_abc",
        ["Compare the three plans", "Just build one plan", "First-timer tips"],
        data={"kind": "plans_abc", "goal": goal, "plans": plans},
    )


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def tools_search(topics: list[str]) -> list[dict]:
    from app.agent import tools

    return tools.search_sessions(topics).get("sessions", [])


def topics_label(topics: list[str]) -> str:
    if not topics:
        return "recommended"
    if len(topics) == 1:
        return topics[0]
    return ", ".join(topics[:-1]) + " and " + topics[-1]


def _reply(reply: str, intent: str, suggestions: list[str], data: dict | None = None) -> dict:
    return {
        "reply": reply,
        "intent": intent,
        "suggestions": suggestions,
        "data": data or {"kind": None},
    }
