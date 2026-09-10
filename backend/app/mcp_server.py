"""reinvent-2026 MCP server.

Exposes the re:Invent 2026 catalog + intelligence as Model Context Protocol
tools so ANY MCP client (the Re:Route Strands agent, Kiro, Claude Desktop, …)
can attach them. It reuses the existing providers, semantic engine, venue model
and official links — no logic is duplicated here.

Run (stdio):
    python -m app.mcp_server

Tools:
    scrape_catalog          — load the catalog (import text/file, or Playwright scrape)
    search_sessions         — keyword/topic search
    search_sessions_semantic— meaning-based search (embeddings)
    get_session             — one session by id
    list_venues             — the six venues + campus travel notes
    estimate_travel         — walk/shuttle time between two venues
    official_links          — authoritative AWS re:Invent URLs
    catalog_status          — current source (imported/scraped/demo) + count
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app import scraper
from app.agent import tools as agent_tools
from app.engine import semantic
from app.official_links import OFFICIAL_LINKS
from app.providers import reinvent_data

mcp = FastMCP("reinvent-2026")

# A live provider we can (re)load with scraped/imported data at runtime.
_SESSIONS = agent_tools.SESSIONS


def _load_into_provider(sessions) -> int:
    if not sessions:
        return 0
    if hasattr(_SESSIONS, "load_sessions"):
        return _SESSIONS.load_sessions(sessions)
    return 0


@mcp.tool()
def scrape_catalog(
    mode: str = "public",
    url: str = scraper.DEFAULT_CATALOG_URL,
    text: str = "",
    fmt: str = "json",
    file_path: str = "",
    storage_state_path: str = "",
) -> dict:
    """Acquire the re:Invent 2026 session catalog and load it as the active source.

    mode:
      "api"     — RECOMMENDED. Page through the official public catalog JSON API
                  (via Playwright) and load all ~1,500 sessions. No login needed.
      "import"  — parse `text` (JSON/CSV) you already exported.
      "file"    — read `file_path` (JSON/CSV export).
      "public"  — Playwright-render the public catalog URL (DOM extraction).
      "auth"    — Playwright-render using `storage_state_path` (your saved login).
    Returns count + a note. Loads the sessions so search tools use them.
    """
    if mode == "api":
        res = scraper.scrape_api()
    elif mode == "import":
        res = scraper.load_from_text(text, fmt)
    elif mode == "file":
        res = scraper.load_from_file(file_path)
    elif mode == "auth":
        res = scraper.scrape_authenticated(url, storage_state_path or None)
    else:
        res = scraper.scrape_public_url(url)
    loaded = _load_into_provider(res.sessions)
    d = res.to_dict()
    d["loaded_into_active_source"] = loaded
    d["source"] = getattr(_SESSIONS, "source", "demo") if loaded else res.source
    return d


@mcp.tool()
def search_sessions(topics: list[str] | None = None, day: str = "", venue: str = "") -> dict:
    """Search re:Invent sessions by topic keywords, optional day and venue."""
    return agent_tools.search_sessions(topics or [], day or None, venue or None)


@mcp.tool()
def search_sessions_semantic(query: str, top_k: int = 8) -> dict:
    """Search sessions by MEANING (embeddings) from a natural-language goal."""
    return agent_tools.search_sessions_semantic(query, top_k)


@mcp.tool()
def get_session(session_id: str) -> dict:
    """Get full details for one session by id."""
    return agent_tools.get_session_details(session_id)


@mcp.tool()
def list_venues() -> dict:
    """List the six re:Invent 2026 venues with type and accessibility info."""
    return {"venues": reinvent_data.VENUES}


@mcp.tool()
def estimate_travel(from_venue: str, to_venue: str) -> dict:
    """Estimate campus travel between two venues (walk vs. shuttle, minutes)."""
    t = reinvent_data.venue_travel(from_venue, to_venue)
    return {"from": from_venue, "to": to_venue, **t}


@mcp.tool()
def official_links() -> dict:
    """Official AWS re:Invent 2026 URLs — the authoritative source of truth."""
    return OFFICIAL_LINKS


@mcp.tool()
def catalog_status() -> dict:
    """Report the active session source and how many sessions are loaded."""
    total = len(agent_tools.search_sessions([]).get("sessions", []))
    return {
        "source": getattr(_SESSIONS, "source", "demo"),
        "session_count": total,
        "embedding_provider": semantic.get_index().provider.name,
    }


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
