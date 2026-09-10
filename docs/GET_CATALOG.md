# Getting the re:Invent session catalog into Re:Route AI

The official catalog pages are JavaScript apps served by Cvent:

- Catalog: `https://registration.awsevents.com/flow/awsevents/reinvent2026/eventcatalog/page/eventcatalog`
- Session types & levels: `.../page/sessiontypeslevels`

The session data is **not in the page HTML** — it loads after the app boots and,
for the full catalog, after you sign in. So there is no server-side URL to
scrape. Re:Route AI is designed around this: you (the signed-in attendee) obtain
the catalog once, and import it.

There are three user-initiated ways, from easiest to most complete.

---

## Option 1 — Paste/upload an export (recommended)

If you can export the catalog (or a saved "My Agenda") to JSON or CSV, just
paste it into **Sessions → Import catalog** in the app, or POST it:

```bash
curl -X POST http://localhost:8000/api/catalog/import \
  -H "Content-Type: application/json" \
  -d '{"catalog_text":"{\"sessions\":[ ... ]}","format":"json"}'
```

Field names are matched flexibly (`title`/`name`, `startTime`/`starts_at`,
`track`/`topic`, `level`, `venue`, `room`, `code`). Only a `title` and a `start`
time are strictly required per session. See
`backend/app/providers/catalog_provider.py → FIELD_ALIASES`.

---

## Option 2 — Grab it from the page you're already viewing (browser console)

This is **user-initiated** and runs in *your* logged-in browser tab — you are
only reading data you already have access to. Respect the event terms of use and
keep it to personal planning.

1. Open the catalog page and sign in.
2. Scroll so sessions load (or open "All sessions").
3. Open DevTools (F12) → **Console**, paste this, press Enter. It scans the
   page's data and copies a clean JSON export to your clipboard:

```js
// Re:Route AI — catalog grabber (personal use).
// Tries the app's in-memory data first, then falls back to visible cards.
(() => {
  const out = [];
  const seen = new Set();
  const push = (o) => {
    if (!o || !o.title) return;
    const key = (o.code || o.title) + (o.startTime || '');
    if (seen.has(key)) return; seen.add(key);
    out.push(o);
  };

  // 1) Look for JSON blobs the app already loaded on the page.
  document.querySelectorAll('script[type="application/json"]').forEach((s) => {
    try {
      const j = JSON.parse(s.textContent);
      const arr = j.sessions || j.data || j.items || (Array.isArray(j) ? j : []);
      arr.forEach((r) => push({
        code: r.code || r.sessionCode || r.abbreviation,
        title: r.title || r.name,
        track: r.track || r.topic || (r.tracks && r.tracks[0]),
        sessionType: r.sessionType || r.type,
        level: r.level,
        venue: r.venue || r.location,
        room: r.room || r.roomName,
        startTime: r.startTime || r.startDateTime,
        endTime: r.endTime || r.endDateTime,
      }));
    } catch (e) {}
  });

  // 2) Fallback: read visible session cards (selectors may need tweaking).
  if (out.length === 0) {
    document.querySelectorAll('[class*="session"], [data-session], article').forEach((el) => {
      const title = el.querySelector('h2,h3,[class*="title"]')?.textContent?.trim();
      const time = el.querySelector('time')?.getAttribute('datetime')
        || el.querySelector('[class*="time"]')?.textContent?.trim();
      if (title) push({ title, startTime: time });
    });
  }

  const json = JSON.stringify({ sessions: out }, null, 2);
  copy(json); // DevTools helper: puts it on your clipboard
  console.log(`Re:Route AI: captured ${out.length} sessions. Copied to clipboard.`);
  return out.length;
})();
```

4. Paste the clipboard into **Sessions → Import catalog** (or save it as a
   `.json` file and set `REROUTE_SESSION_CATALOG`).

> The exact card selectors on Cvent change over time. If the fallback finds 0
> sessions, the JSON-blob path (step 1) usually still works once all sessions
> are loaded. Adjust the selectors to match the current DOM if needed.

---

## Option 3 — Point the backend at a saved file

Save any JSON/CSV export to disk and start the backend with:

```powershell
$env:REROUTE_SESSION_CATALOG = "d:\path\to\reinvent2026_sessions.json"
uvicorn app.api:app --port 8000
```

---

## What about "Session types & levels"?

That page is static reference information (what a Breakout / Workshop / Chalk
Talk is, and what content levels 100–400 mean). It is built into the app —
`GET /api/session-types`, and the agent's `explain_session_types` tool — so no
scraping is needed. The planner uses it to balance hands-on vs. lecture formats
and to reason about session difficulty.

---

## Why not scrape the URL automatically?

- The pages are empty JS shells; the data is behind a login-gated private API.
- Automating a logged-in session (e.g. with headless browser + your AWS
  credentials) is brittle and discouraged by the event terms of use.
- A one-time, user-initiated export is reliable, respectful of the ToS, and
  keeps your credentials out of the app.
