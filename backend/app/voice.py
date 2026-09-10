"""Voice capability for Re:Route AI — multi-purpose, hands-free use.

Text-to-speech uses Amazon Polly when AWS credentials are available (returns
MP3 audio bytes). When Polly isn't reachable (local/hackathon dev), the API
signals the frontend to use the browser's built-in speechSynthesis instead, so
voice always works.

Speech-to-text (mission dictation) is handled client-side with the browser Web
Speech API for zero-latency demo use; Amazon Transcribe is the documented
production swap (same request/response shape can be added here later).

Everything is optional and degrades gracefully — no hard dependency on boto3.
"""
from __future__ import annotations

import os

# Amazon Polly neural voices. A small, useful multi-accent selection.
POLLY_VOICES: list[dict] = [
    {"id": "Matthew", "label": "Matthew (US, male)", "engine": "neural", "lang": "en-US"},
    {"id": "Joanna", "label": "Joanna (US, female)", "engine": "neural", "lang": "en-US"},
    {"id": "Amy", "label": "Amy (UK, female)", "engine": "neural", "lang": "en-GB"},
    {"id": "Kajal", "label": "Kajal (Indian English, female)", "engine": "neural", "lang": "en-IN"},
    {"id": "Arjun", "label": "Arjun (Indian English, male)", "engine": "neural", "lang": "en-IN"},
]
DEFAULT_VOICE = os.getenv("REROUTE_POLLY_VOICE", "Matthew")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

_polly_client = None
_polly_error: str | None = None


def _get_polly():
    global _polly_client, _polly_error
    if _polly_client is None and _polly_error is None:
        try:
            import boto3

            _polly_client = boto3.client("polly", region_name=AWS_REGION)
        except Exception as exc:  # pragma: no cover - depends on env
            _polly_error = f"{type(exc).__name__}: {exc}"
    return _polly_client


def polly_available() -> bool:
    """Only claim Polly when explicitly enabled and constructible."""
    if os.getenv("REROUTE_USE_POLLY", "").lower() not in ("1", "true", "yes"):
        return False
    return _get_polly() is not None


def voice_config() -> dict:
    return {
        "polly_available": polly_available(),
        "provider": "amazon-polly" if polly_available() else "browser-speech-synthesis",
        "voices": POLLY_VOICES,
        "default_voice": DEFAULT_VOICE,
        "stt_provider": "browser-web-speech-api",  # Amazon Transcribe = production swap
        "region": AWS_REGION,
    }


def synthesize(text: str, voice_id: str | None = None) -> bytes | None:
    """Return MP3 audio bytes from Amazon Polly, or None if unavailable
    (frontend then falls back to browser TTS)."""
    if not polly_available():
        return None
    client = _get_polly()
    voice = voice_id if voice_id in {v["id"] for v in POLLY_VOICES} else DEFAULT_VOICE
    try:  # pragma: no cover - network dependent
        resp = client.synthesize_speech(
            Text=text[:2900],  # Polly per-request limit safety
            OutputFormat="mp3",
            VoiceId=voice,
            Engine="neural",
        )
        stream = resp.get("AudioStream")
        return stream.read() if stream else None
    except Exception:
        return None
