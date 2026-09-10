"""RAG knowledge base of past re:Invent experience & preparation tips.

Loads tips from data/reinvent_tips.json (user-editable), embeds them once with
the same embedding provider used for semantic session search, and retrieves the
most relevant tips for a mission/query by cosine similarity. The agent uses the
retrieved tips to give grounded, cited preparation advice — it never fabricates
tips; it only surfaces and lightly comments on what's in the knowledge base.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from app.providers.embeddings import cosine, get_embedding_provider

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reinvent_tips.json")


@dataclass
class Tip:
    id: str
    text: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    score: float = 0.0

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "tags": self.tags,
                "source": self.source, "score": round(self.score, 3)}


class KnowledgeBase:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("REROUTE_TIPS_FILE") or _DEFAULT_PATH
        self.provider = get_embedding_provider()
        self._tips: list[Tip] = []
        self._vecs: dict[str, list[float]] = {}
        self.loaded = False
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("tips", data) if isinstance(data, dict) else data
            self._tips = [
                Tip(
                    id=str(r.get("id") or f"tip-{i}"),
                    text=str(r.get("text", "")).strip(),
                    tags=list(r.get("tags", [])),
                    source=str(r.get("source", "")),
                )
                for i, r in enumerate(rows)
                if str(r.get("text", "")).strip()
            ]
            self._vecs = {t.id: self.provider.embed(t.text + " " + " ".join(t.tags)) for t in self._tips}
            self.loaded = bool(self._tips)
        except Exception:
            self._tips, self._vecs, self.loaded = [], {}, False

    def add_tips(self, rows: list[dict]) -> int:
        """Add tips at runtime (e.g. user-provided data)."""
        start = len(self._tips)
        for i, r in enumerate(rows):
            text = str(r.get("text", "")).strip()
            if not text:
                continue
            t = Tip(id=str(r.get("id") or f"tip-{start + i}"), text=text,
                    tags=list(r.get("tags", [])), source=str(r.get("source", "")))
            self._tips.append(t)
            self._vecs[t.id] = self.provider.embed(t.text + " " + " ".join(t.tags))
        self.loaded = bool(self._tips)
        return len(self._tips)

    def count(self) -> int:
        return len(self._tips)

    def retrieve(self, query: str, top_k: int = 4) -> list[Tip]:
        if not self._tips:
            return []
        qv = self.provider.embed(query)
        scored: list[Tip] = []
        for t in self._tips:
            t2 = Tip(t.id, t.text, t.tags, t.source, cosine(qv, self._vecs[t.id]))
            scored.append(t2)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def advise(query: str, top_k: int = 4) -> dict:
    """Return relevant tips + a short, grounded commentary for the UI/agent."""
    kb = get_kb()
    tips = kb.retrieve(query, top_k)
    commentary = _commentary(query, tips)
    return {
        "query": query,
        "tips": [t.to_dict() for t in tips],
        "commentary": commentary,
        "knowledge_count": kb.count(),
    }


def _commentary(query: str, tips: list[Tip]) -> str:
    """A brief, grounded lead-in — references the retrieved tips, invents nothing."""
    if not tips:
        return "No preparation tips found yet. Add past experience to the knowledge base."
    top = tips[0]
    themes = sorted({tag for t in tips for tag in t.tags})[:4]
    theme_str = ", ".join(themes) if themes else "your trip"
    return (
        f"Based on past re:Invent experience, the most relevant advice for your goal "
        f"touches on {theme_str}. Start with: \"{top.text}\""
    )
