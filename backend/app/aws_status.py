"""AWS services integration status.

One place that reports which AWS services Re:Route AI is actually using, and
whether each is reachable with the current credentials. Everything is optional
and degrades gracefully — this module never raises; it just reports.

Services surfaced:
  * Amazon Bedrock (Strands agent model — Nova / Claude)
  * Amazon Bedrock Titan Text Embeddings (semantic search)
  * Amazon Polly (text-to-speech)
  * boto3 / credentials presence
  * MCP session source (reinvent2026-mcp)

Toggle each with env vars (see below). With no AWS setup, the app runs fully on
deterministic/local fallbacks.
"""
from __future__ import annotations

import os


def _boto3_available() -> bool:
    try:
        import boto3  # noqa: F401

        return True
    except Exception:
        return False


def _has_credentials() -> bool:
    """Best-effort check that AWS credentials resolve (no network call)."""
    if not _boto3_available():
        return False
    try:
        import boto3

        creds = boto3.Session().get_credentials()
        return creds is not None
    except Exception:
        return False


def bedrock_model_status() -> dict:
    from app.agent import strands_agent as sa

    return {
        "enabled": sa.model_available(),
        "active_model": sa.active_model(),
        "region": sa.AWS_REGION,
        "toggle_env": "REROUTE_USE_STRANDS_MODEL=1",
    }


def embeddings_status() -> dict:
    from app.providers import embeddings

    return {
        "provider": embeddings.provider_name(),  # "bedrock-titan" | "local-hash"
        "using_bedrock": embeddings.provider_name() == "bedrock-titan",
        "model": os.getenv("REROUTE_EMBED_MODEL", "amazon.titan-embed-text-v2:0"),
        "toggle_env": "REROUTE_USE_BEDROCK_EMBEDDINGS=1",
    }


def polly_status() -> dict:
    from app import voice

    return {
        "using_polly": voice.polly_available(),
        "provider": "amazon-polly" if voice.polly_available() else "browser-speech-synthesis",
        "toggle_env": "REROUTE_USE_POLLY=1",
    }


def session_source_status() -> dict:
    from app.agent import tools

    src = getattr(tools.SESSIONS, "source", "demo")
    return {"source": src, "mcp": src == "mcp", "toggle_env": "REROUTE_USE_MCP=1"}


def aws_status() -> dict:
    """Full AWS integration snapshot."""
    boto3_ok = _boto3_available()
    creds_ok = _has_credentials()
    bedrock = bedrock_model_status()
    embed = embeddings_status()
    polly = polly_status()
    src = session_source_status()

    any_live = bedrock["enabled"] or embed["using_bedrock"] or polly["using_polly"]

    return {
        "region": os.getenv("AWS_REGION", "us-west-2"),
        "boto3_installed": boto3_ok,
        "credentials_resolved": creds_ok,
        "any_aws_service_live": any_live,
        "services": {
            "bedrock_agent": bedrock,
            "bedrock_embeddings": embed,
            "polly_tts": polly,
            "session_source": src,
        },
        "note": (
            "Set the toggle_env vars + AWS credentials to enable each real AWS "
            "service. Without them, the app uses deterministic/local fallbacks."
        ),
    }
