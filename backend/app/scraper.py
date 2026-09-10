"""re:Invent catalog scraper / data loader.

The official catalog page is a Cvent single-page app: the HTML is an empty shell
and the sessions load via JavaScript, with the full catalog behind login. This
module offers layered strategies, most-reliable first:

  1. load_from_text / load_from_file  — ingest an export you already have.
  2. scrape_public_url(url)           — render the page with Playwright and
     extract any JSON/DOM sessions present (works for public pages; for the
     login-gated catalog it returns what loads pre-login + a clear note).
  3. scrape_authenticated(url, storage_state)
                                      — Playwright reusing YOUR saved login
     session (you sign in once; the storage state is reused). This can reach the
     full catalog, staying within your own access.

All strategies normalize results through the existing catalog parser so the
Session shape is identical everywhere. Playwright is optional; if it isn't
installed the scrape_* functions return a helpful, non-fatal message.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.models import Session
from app.providers.catalog_provider import load_catalog_from_text

DEFAULT_CATALOG_URL = (
    "https://registration.awsevents.com/flow/awsevents/reinvent2026/"
    "eventcatalog/page/eventcatalog"
)


@dataclass
class ScrapeResult:
    ok: bool
    source: str
    sessions: list[Session] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "source": self.source,
            "count": len(self.sessions),
            "note": self.note,
            "sessions": [s.model_dump(mode="json") for s in self.sessions],
        }


# --------------------------------------------------------------------------- #
# 1) Import an existing export (reliable)
# --------------------------------------------------------------------------- #
def load_from_text(text: str, fmt: str = "json") -> ScrapeResult:
    sessions = load_catalog_from_text(text, fmt)
    return ScrapeResult(
        ok=bool(sessions),
        source="import-text",
        sessions=sessions,
        note="Loaded from provided export." if sessions else "No sessions parsed.",
    )


def load_from_file(path: str) -> ScrapeResult:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return ScrapeResult(ok=False, source="import-file", note=f"File not found: {path}")
    fmt = "csv" if p.suffix.lower() == ".csv" else "json"
    return load_from_text(p.read_text(encoding="utf-8"), fmt)


# --------------------------------------------------------------------------- #
# Shared JSON extraction from a rendered page
# --------------------------------------------------------------------------- #
def _extract_sessions_from_html(html: str) -> list[Session]:
    """Pull session-like objects out of embedded JSON in a rendered page."""
    rows: list[dict] = []
    # Cvent apps typically embed data in <script type="application/json"> or
    # window.__STATE__ = {...}. Try both.
    for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        rows += _harvest(data)
    for m in re.finditer(r'window\.__[A-Z_]+__\s*=\s*(\{.*?\});', html, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        rows += _harvest(data)
    if not rows:
        return []
    # Normalize through the shared parser (handles field aliases + enrichment).
    return load_catalog_from_text(json.dumps({"sessions": rows}), "json")


def _harvest(data) -> list[dict]:
    """Find lists of session-like dicts anywhere in a nested JSON structure."""
    found: list[dict] = []

    def looks_like_session(d: dict) -> bool:
        keys = {k.lower() for k in d.keys()}
        has_title = keys & {"title", "name", "sessiontitle"}
        has_time = keys & {"starttime", "start", "startdatetime", "startsat"}
        return bool(has_title and has_time)

    def walk(node):
        if isinstance(node, dict):
            if looks_like_session(node):
                found.append(node)
            else:
                for v in node.values():
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return found


# --------------------------------------------------------------------------- #
# 2) Public URL render (Playwright)
# --------------------------------------------------------------------------- #
def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except Exception:
        return False


_LOGIN_GATE_NOTE = (
    "This catalog is a login-gated Cvent app. Anonymous rendering usually yields "
    "0 sessions because the full catalog loads only after sign-in. Use "
    "scrape_authenticated with a saved login session, or import an export."
)


def scrape_api(max_sessions: int | None = None) -> ScrapeResult:
    """Best strategy: call the public catalog JSON API via Playwright and page
    through ALL sessions (no login needed — the catalog is anonymously browsable)."""
    from app import aws_catalog

    if not aws_catalog.playwright_available():
        return ScrapeResult(
            ok=False, source="scrape-api",
            note="Playwright not installed. Run: pip install playwright && playwright install chromium",
        )
    try:  # pragma: no cover - requires a browser at runtime
        sessions = aws_catalog.fetch_all(max_sessions=max_sessions)
        return ScrapeResult(
            ok=bool(sessions), source="scrape-api", sessions=sessions,
            note=f"Fetched {len(sessions)} sessions from the official catalog API.",
        )
    except Exception as exc:
        return ScrapeResult(ok=False, source="scrape-api", note=f"Catalog API scrape failed: {exc}")


def scrape_public_url(url: str = DEFAULT_CATALOG_URL, wait_ms: int = 6000) -> ScrapeResult:
    if not _playwright_available():
        return ScrapeResult(
            ok=False, source="scrape-public",
            note="Playwright not installed. Run: pip install playwright && playwright install chromium",
        )
    try:  # pragma: no cover - requires a browser at runtime
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            browser.close()
        sessions = _extract_sessions_from_html(html)
        return ScrapeResult(
            ok=bool(sessions), source="scrape-public", sessions=sessions,
            note="Rendered public page." if sessions else _LOGIN_GATE_NOTE,
        )
    except Exception as exc:
        return ScrapeResult(ok=False, source="scrape-public", note=f"Scrape failed: {exc}")


# --------------------------------------------------------------------------- #
# 3) Authenticated render (Playwright + saved storage state)
# --------------------------------------------------------------------------- #
def scrape_authenticated(
    url: str = DEFAULT_CATALOG_URL, storage_state_path: str | None = None, wait_ms: int = 8000
) -> ScrapeResult:
    """Render the catalog using a previously-saved login session.

    Create the storage state once (user-initiated):
        playwright open --save-storage=reinvent_state.json <login-url>
    then sign in, close the window. Pass that file here.
    """
    if not _playwright_available():
        return ScrapeResult(
            ok=False, source="scrape-auth",
            note="Playwright not installed. Run: pip install playwright && playwright install chromium",
        )
    if not storage_state_path:
        return ScrapeResult(
            ok=False, source="scrape-auth",
            note="Provide storage_state_path (a saved logged-in session). See docs/GET_CATALOG.md.",
        )
    try:  # pragma: no cover - requires a browser + real session at runtime
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(storage_state=storage_state_path)
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(wait_ms)
            # Scroll to trigger lazy loading of all session cards.
            for _ in range(8):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(600)
            html = page.content()
            browser.close()
        sessions = _extract_sessions_from_html(html)
        return ScrapeResult(
            ok=bool(sessions), source="scrape-auth", sessions=sessions,
            note=f"Rendered authenticated catalog ({len(sessions)} sessions)."
            if sessions else "Signed-in render returned no parseable sessions; the DOM may have changed.",
        )
    except Exception as exc:
        return ScrapeResult(ok=False, source="scrape-auth", note=f"Authenticated scrape failed: {exc}")
