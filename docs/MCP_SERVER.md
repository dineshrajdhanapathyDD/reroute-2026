# reinvent-2026 MCP server

Re:Route AI ships a **Model Context Protocol (MCP)** server that exposes the
re:Invent 2026 catalog + intelligence as tools any MCP client can attach —
including the Re:Route Strands agent, Kiro, and Claude Desktop.

```
                 ┌─────────────────────────────────────┐
   export / URL  │  reinvent-2026 MCP server (stdio)     │
   ─────────────►│  reuses providers · semantic · venues │
                 │  tools:                               │
                 │   scrape_catalog                      │
                 │   search_sessions                     │
                 │   search_sessions_semantic            │
                 │   get_session · list_venues           │
                 │   estimate_travel · official_links    │
                 │   catalog_status                      │
                 └──────────────┬──────────────────────── ┘
                                │ MCP (JSON-RPC over stdio)
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                         ▼
  Strands agent            Kiro IDE                Claude Desktop
  (REROUTE_ATTACH_MCP=1)   (.kiro/settings/mcp.json)   (any client)
```

The server **reuses the existing code** — providers, the catalog parser, the
semantic engine, the venue model, and official links. Nothing is duplicated.

## Tools

| Tool | What it does |
|------|--------------|
| `scrape_catalog` | Acquire the catalog and load it as the active source. Modes: `import` (paste JSON/CSV), `file`, `public` (Playwright render), `auth` (Playwright + your saved login). |
| `search_sessions` | Keyword/topic search (+ optional day/venue). |
| `search_sessions_semantic` | Meaning-based search from a natural-language goal (embeddings). |
| `get_session` | One session by id. |
| `list_venues` | The six venues + type/accessibility. |
| `estimate_travel` | Walk vs. shuttle minutes between two venues. |
| `official_links` | Authoritative AWS re:Invent URLs. |
| `catalog_status` | Active source (imported/scraped/demo) + session count. |

## Run it

```bash
cd backend
python -m app.mcp_server        # stdio transport; waits for an MCP client
```

## Attach it

### A) To the Re:Route Strands agent
```powershell
$env:REROUTE_ATTACH_MCP = "1"
$env:REROUTE_USE_STRANDS_MODEL = "1"   # + AWS Bedrock creds
uvicorn app.api:app --port 8000
```
The Navigator connects to the MCP server over stdio and exposes its tools to the
Bedrock model alongside the native tools.

### B) To Kiro / Claude Desktop
Copy `mcp.json` (repo root) into your client's MCP config
(e.g. `.kiro/settings/mcp.json`). The `reinvent-2026` server appears with its
tools; read-only tools are auto-approved.

## The scraper — it works, and it's real

We found that the catalog page loads its data from a **public JSON API**:
`POST https://catalog.awsevents.com/api/sessions`. It needs two profile headers
(`rfapiprofileid`, `rfwidgetid`) that the page generates — **no login required**;
the catalog is anonymously browsable. So the scraper opens the page once with
Playwright, captures those headers, then pages through all ~1,500 sessions.

`scrape_catalog` strategies, best first:

1. **`api`** — RECOMMENDED. Page through the official catalog JSON API via
   Playwright. Pulls the full ~1,500-session catalog (real titles, types,
   levels, topics, abstracts). This is how the bundled catalog was produced.
2. **`import` / `file`** — ingest an export you already have. Always works.
3. **`public`** — Playwright renders the page and extracts embedded JSON/DOM.
4. **`auth`** — Playwright renders reusing your saved login session (only needed
   for personalized/reserved data behind sign-in).

### Bundled real catalog

The repo ships `backend/data/reinvent2026_sessions.json` — the real 1,507-session
re:Invent 2026 catalog, scraped and normalized. The app loads it **by default**
(so `session_source: catalog`, `demo_mode: false` out of the box). Refresh it any
time:

```bash
cd backend
python scripts/refresh_catalog.py    # re-scrapes the official API
```

> Note: the public catalog does not publish per-session times/rooms until nearer
> the event, so day/time/venue are assigned deterministically (clearly labelled
> estimated placement) to make scheduling and the map usable. Real published
> times can replace them later without any code change.

### Set up the authenticated session once (user-initiated)
```bash
pip install playwright && playwright install chromium
# Sign in, then close the window — this saves your session:
playwright open --save-storage=reinvent_state.json \
  "https://registration.awsevents.com/flow/awsevents/reinvent2026/login"
```
Then:
```
scrape_catalog(mode="auth",
               storage_state_path="reinvent_state.json",
               url="https://registration.awsevents.com/flow/awsevents/reinvent2026/eventcatalog/page/eventcatalog")
```

> Automated access is governed by the event's terms of use. Keep it to your own
> personal planning. When in doubt, use the `import` path with an export.

However the data arrives, it is normalized through the same parser and
enrichment as everything else, so `search_sessions`, semantic search, conflict
detection, and the daily schedule all just work.
```
