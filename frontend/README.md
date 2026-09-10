# Re:Route AI — Frontend

The web UI for Re:Route AI, an AI learning-navigator for AWS re:Invent 2026.
Built with React 19 + TypeScript + Vite + Tailwind CSS. It talks to the FastAPI
backend and falls back to bundled sample data when the API is unreachable, so the
UI always renders.

## Run

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`. In dev, `/api` is proxied to the backend on
`:8000` (see `vite.config.ts`). The app starts on the **Chat** page.

## Build

```bash
npm run build     # tsc + vite build -> dist/
npm run preview   # preview the production build
```

Set the deployed backend URL in `.env.production` (`VITE_API_BASE`). In dev this
is left empty and the Vite proxy is used instead.

## Structure

```
src/
├── pages/          # Chat (landing), Mission, Plans (A/B/C), Sessions, Explore,
│                   # Prep, Learning, ReRoute, Wayfinder, Journey, Schedule, Settings
├── components/
│   ├── ui/         # Button, Card, Badge, Modal, Toast, ProgressRing, …
│   ├── layout/     # AppShell, Sidebar, Header, MobileNav
│   └── agent/      # AgentStatus, AgentActivity, ApprovalDialog, …
└── lib/            # api.ts (typed client), mappers.ts, mission store, types
```

## Data flow

Pages read from the mission store (`src/lib/mission.tsx`), which calls the
backend via the typed client in `src/lib/api.ts` and maps backend shapes into UI
types (`src/lib/mappers.ts`). `src/lib/mockData.ts` is fallback-only.
