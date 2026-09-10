"""Embedding providers for semantic session search.

An EmbeddingProvider turns text into a vector so we can rank sessions by meaning
(cosine similarity) instead of keyword overlap. Two implementations:

  * BedrockEmbeddingProvider — Amazon Bedrock Titan Text Embeddings (real).
  * LocalHashEmbeddingProvider — a deterministic, dependency-free fallback that
    works with no AWS creds so the demo always runs. It is a bag-of-words hashing
    embedder: not as good as Titan, but good enough to demonstrate semantic-style
    ranking (synonyms via a small lexicon, token overlap, etc.).

`get_embedding_provider()` picks Bedrock when enabled + reachable, else local.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from abc import ABC, abstractmethod

# Small synonym/related-term lexicon so the local embedder captures some meaning
# (e.g. "build" ~ "hands-on", "production" ~ "deploy"). Each concept maps to a
# stable dimension group; related words share dimensions.
_CONCEPTS: dict[str, list[str]] = {
    "agent": ["agent", "agents", "agentic", "agentcore", "autonomous", "orchestrate", "multiagent"],
    "genai": ["generative", "genai", "llm", "foundation", "model", "gpt", "prompt", "rag"],
    "bedrock": ["bedrock", "titan", "anthropic", "claude", "nova"],
    "handson": ["workshop", "lab", "builder", "builders", "build", "hands", "handson", "implement", "code"],
    "production": ["production", "deploy", "deployment", "operate", "operations", "observability", "scale", "reliability"],
    "security": ["security", "secure", "iam", "encryption", "guardrail", "threat", "compliance"],
    "serverless": ["serverless", "lambda", "fargate", "eventbridge", "stepfunctions"],
    "data": ["data", "analytics", "database", "redshift", "aurora", "vector", "embedding"],
    "architecture": ["architecture", "design", "wellarchitected", "pattern", "reference"],
    "certification": ["certification", "exam", "certify", "specialty", "bootcamp"],
}
_DIM = 128
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(ABC):
    name: str = "base"

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic bag-of-words hashing embedder with a concept lexicon.

    No external calls. Tokens hash into a fixed vector; concept words also add
    weight to a stable concept dimension so semantically-related phrasing lands
    near each other.
    """

    name = "local-hash"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        tokens = _TOKEN_RE.findall((text or "").lower())
        # concept mapping: word -> concept index
        word_concept = {}
        for i, (_concept, words) in enumerate(_CONCEPTS.items()):
            for w in words:
                word_concept[w] = i
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
            if tok in word_concept:
                # concept dims live in the top region for strong signal
                vec[_DIM - 1 - (word_concept[tok] % (_DIM // 4))] += 2.5
        return vec


class BedrockEmbeddingProvider(EmbeddingProvider):
    """Amazon Bedrock Titan Text Embeddings v2."""

    name = "bedrock-titan"

    def __init__(self, model_id: str | None = None, region: str | None = None):
        import boto3  # imported lazily; only when Bedrock is enabled

        self.model_id = model_id or os.getenv("REROUTE_EMBED_MODEL", "amazon.titan-embed-text-v2:0")
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    def embed(self, text: str) -> list[float]:  # pragma: no cover - network dependent
        import json

        resp = self._client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({"inputText": text[:8000]}),
        )
        payload = json.loads(resp["body"].read())
        return payload["embedding"]


_provider: EmbeddingProvider | None = None


def bedrock_enabled() -> bool:
    return os.getenv("REROUTE_USE_BEDROCK_EMBEDDINGS", "").lower() in ("1", "true", "yes")


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is not None:
        return _provider
    if bedrock_enabled():
        try:
            _provider = BedrockEmbeddingProvider()
            return _provider
        except Exception:  # pragma: no cover - falls back if boto3/creds missing
            pass
    _provider = LocalHashEmbeddingProvider()
    return _provider


def provider_name() -> str:
    return get_embedding_provider().name
