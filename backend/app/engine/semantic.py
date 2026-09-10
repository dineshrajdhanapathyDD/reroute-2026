"""Semantic session search.

Embeds each session's text (title + topic + format + level) once, caches the
vectors, and ranks a natural-language query by cosine similarity. The final
relevance blends the semantic score with the session's existing keyword
match_score so results are robust either way.
"""
from __future__ import annotations

from app.models import Session
from app.providers.embeddings import EmbeddingProvider, cosine, get_embedding_provider


def session_text(s: Session) -> str:
    return f"{s.title}. Topic: {s.topic}. Format: {s.format}. Level {s.level}. Mode: {s.learning_mode}."


class SemanticSessionIndex:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or get_embedding_provider()
        self._vectors: dict[str, list[float]] = {}
        self._text_hash: dict[str, str] = {}

    def index(self, sessions: list[Session]) -> None:
        # Only embed sessions we haven't cached yet (persists across requests in
        # a warm process/Lambda), and batch the embed calls when the provider
        # supports it (Titan) to avoid N sequential network round-trips.
        todo: list[Session] = []
        for s in sessions:
            txt = session_text(s)
            if self._text_hash.get(s.id) != txt:
                todo.append(s)
        if not todo:
            return
        texts = [session_text(s) for s in todo]
        try:
            vectors = self.provider.embed_many(texts)
        except Exception:
            vectors = [self.provider.embed(t) for t in texts]
        for s, txt, vec in zip(todo, texts, vectors):
            self._vectors[s.id] = vec
            self._text_hash[s.id] = txt

    def rank(
        self, query: str, sessions: list[Session], blend_keyword: float = 0.35
    ) -> list[tuple[Session, int, float]]:
        """Return [(session, blended_score_0_100, semantic_similarity)] sorted best-first.

        blended = (1-blend)*semantic + blend*(keyword match_score/100)
        """
        self.index(sessions)
        qv = self.provider.embed(query)
        results: list[tuple[Session, int, float]] = []
        for s in sessions:
            sim = cosine(qv, self._vectors.get(s.id, []))
            sem = max(0.0, min(1.0, sim))
            kw = (s.match_score or 0) / 100.0
            blended = (1 - blend_keyword) * sem + blend_keyword * kw
            results.append((s, round(blended * 100), sim))
        results.sort(key=lambda r: r[1], reverse=True)
        return results


# Module-level singleton index (rebuilds lazily as sessions change).
_index: SemanticSessionIndex | None = None


def get_index() -> SemanticSessionIndex:
    global _index
    if _index is None:
        _index = SemanticSessionIndex()
    return _index


def semantic_search(
    query: str, sessions: list[Session], top_k: int | None = None
) -> list[Session]:
    """Return sessions ranked by semantic relevance, with match_score updated to
    the blended relevance so downstream planning reflects the semantic ranking."""
    ranked = get_index().rank(query, sessions)
    out: list[Session] = []
    for s, blended, _sim in ranked:
        s = s.model_copy()
        s.match_score = blended
        out.append(s)
    return out[:top_k] if top_k else out
