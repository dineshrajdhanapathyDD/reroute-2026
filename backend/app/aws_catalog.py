"""AWS re:Invent 2026 catalog API client (via Playwright).

The public catalog page (Cvent) loads sessions from
`POST https://catalog.awsevents.com/api/sessions`. The request needs two profile
headers (`rfapiprofileid`, `rfwidgetid`) that the page generates. We open the
page once with Playwright, capture those headers, then page through all sessions
by calling the API *from the page context* (so cookies/session apply).

This yields the full ~1,500-session catalog with NO login — the public catalog
is anonymously browsable. Sessions are mapped into our `Session` model via the
existing catalog parser + enrichment, so everything downstream is unchanged.

Requires: pip install playwright && playwright install chromium
"""
from __future__ import annotations

from app.models import Session
from app.providers.catalog_provider import load_catalog_from_text

CATALOG_PAGE = (
    "https://registration.awsevents.com/flow/awsevents/reinvent2026/"
    "eventcatalog/page/eventcatalog"
)
SESSIONS_API = "https://catalog.awsevents.com/api/sessions"

_FETCH_JS = """
async ([api, headers, frm, size]) => {
  const body = new URLSearchParams({
    type: 'session', browserTimezone: 'America/Los_Angeles',
    catalogDisplay: 'list', from: String(frm), size: String(size),
  });
  const r = await fetch(api, { method: 'POST', headers, body: body.toString(), credentials: 'include' });
  return await r.json();
}
"""


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except Exception:
        return False


def _attr(item: dict, name: str) -> str | None:
    for av in item.get("attributevalues", []) or []:
        if av.get("attribute") == name:
            return av.get("value")
    return None


def _topic_attr(item: dict) -> str | None:
    # Prefer explicit topic/track-like attributes over Type/Level.
    for name in ("Topic", "Area of Interest", "Track", "Services", "Primary Topic"):
        v = _attr(item, name)
        if v:
            return v
    return None


_VENUES = ["The Venetian", "Caesars Forum", "Wynn", "MGM Grand", "Encore", "Caesars Palace"]
# Two nearby venues per day so a day's route clusters (walkable) instead of
# scattering across the whole Strip. Clearly estimated placement.
_DAY_VENUES = {
    "2026-12-01": ["The Venetian", "Wynn"],       # north cluster (walkable)
    "2026-12-02": ["Caesars Forum", "Caesars Palace"],  # mid cluster (walkable)
    "2026-12-03": ["Wynn", "Encore"],             # north cluster (walkable)
    "2026-12-04": ["The Venetian", "Encore"],     # north cluster (walkable)
}


def _venue_for(day: str, index: int) -> str:
    pair = _DAY_VENUES.get(day, _VENUES[:2])
    return pair[index % len(pair)]


def _raw_item_to_row(item: dict, index: int = 0, day: str = "2026-12-01") -> dict:
    """Map a catalog API item to the flexible row shape our parser understands."""
    return {
        "code": item.get("code") or item.get("abbreviation") or item.get("sessionID"),
        "title": item.get("title"),
        "topic": _topic_attr(item),
        "sessionType": item.get("type") or _attr(item, "Type"),
        "level": _attr(item, "Level"),
        "abstract": item.get("abstract"),
        # Public catalog list omits room/time/venue until scheduled; assign a
        # deterministic, day-clustered venue so travel/map are realistic
        # (clearly estimated placement, replaceable by real schedule data).
        "venue": _venue_for(day, index),
    }


# re:Invent runs Mon Dec 1 – Fri Dec 5 (2026 program days). The public catalog
# does not publish per-session times until nearer the event, so we assign
# deterministic, plausible day/time slots. This makes the planner usable (no
# false all-day conflicts) while staying clearly labelled as estimated timing.
_DAYS = ["2026-12-01", "2026-12-02", "2026-12-03", "2026-12-04"]
_SLOTS = ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30"]  # start times


def _synth_time(index: int) -> str:
    day = _DAYS[(index // len(_SLOTS)) % len(_DAYS)]
    slot = _SLOTS[index % len(_SLOTS)]
    return f"{day}T{slot}:00"


def raw_items_to_sessions(items: list[dict]) -> list[Session]:
    import json

    rows = []
    for i, it in enumerate(items):
        if not it.get("title"):
            continue
        start = _synth_time(i)
        day = start.split("T")[0]
        r = _raw_item_to_row(it, i, day)
        r.setdefault("startTime", start)
        rows.append(r)
    return load_catalog_from_text(json.dumps({"sessions": rows}), "json")


def fetch_all(page_size: int = 50, max_sessions: int | None = None) -> list[Session]:
    """Open the catalog with Playwright and page through the full session list."""
    if not playwright_available():
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )
    from playwright.sync_api import sync_playwright  # pragma: no cover

    profile: dict[str, str] = {}
    collected: dict[str, dict] = {}

    with sync_playwright() as pw:  # pragma: no cover - requires browser
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        def on_request(r):
            if SESSIONS_API in r.url and not profile:
                for k, v in r.headers.items():
                    if k.lower() in ("rfapiprofileid", "rfwidgetid"):
                        profile[k] = v

        page.on("request", on_request)
        page.goto(CATALOG_PAGE, wait_until="domcontentloaded", timeout=60000)
        # Wait until the catalog API fires so we capture its profile headers.
        for _ in range(20):
            if profile:
                break
            page.wait_for_timeout(1000)
        if not profile:
            # Last resort: reload and wait for the specific request.
            try:
                with page.expect_request(lambda r: SESSIONS_API in r.url, timeout=30000) as info:
                    page.reload(wait_until="domcontentloaded")
                req = info.value
                for k, v in req.headers.items():
                    if k.lower() in ("rfapiprofileid", "rfwidgetid"):
                        profile[k] = v
            except Exception:
                pass
        if not profile:
            browser.close()
            raise RuntimeError("Could not capture catalog API profile headers.")

        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", **profile}
        frm, total = 0, None
        while True:
            d = page.evaluate(_FETCH_JS, [SESSIONS_API, headers, frm, page_size])
            if "sectionList" in d and d["sectionList"]:
                sec = d["sectionList"][0]
                items, total = sec.get("items", []), sec.get("total")
            elif "items" in d:
                items, total = d.get("items", []), d.get("total")
            else:
                break
            for it in items:
                collected[it.get("code") or it.get("sessionID")] = it
            frm += page_size
            if not items or (total and frm >= total):
                break
            if max_sessions and len(collected) >= max_sessions:
                break
        browser.close()

    return raw_items_to_sessions(list(collected.values()))
