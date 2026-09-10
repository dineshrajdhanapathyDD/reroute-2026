# Re:Route AI

> **Never lose your learning path at AWS re:Invent.**
> The destination stays the same. The route can change.

**Agents for Humans hackathon · Track: Professional Agents · Built with the Strands Agents SDK on Amazon Bedrock (Nova).**

Re:Route AI takes a repetitive, time-draining task off an attendee's plate:
building — and constantly re-building — a workable schedule across AWS re:Invent's
1,500+ sessions and six Las Vegas venues. You tell it a learning goal in plain
language (*"I want to get production-ready with AI agents"*) and it builds a
realistic, walkable route. Then it **runs in the background** and only pings you
when a real decision is needed — a session fills up, a route breaks — arriving
with the fix already worked out.

### Try it in 60 seconds

1. **Live demo → https://d315hfgmfqehyn.cloudfront.net** — on the chat page, type
   *"I'm new — build me a plan for learning GenAI"*, then open **Agent Watch**.
2. **Run locally →** see [Run locally](#run-locally) (works with zero AWS
   credentials — a deterministic pipeline stands in for the model).
3. **See the design →** [architecture diagram](docs/architecture.drawio) ·
   [how it works](#how-it-works) · [Agent Watch](#agent-watch--runs-in-the-background-pings-you-only-on-a-decision).

| | |
|---|---|
| **Live demo** | https://d315hfgmfqehyn.cloudfront.net |
| **Agent framework** | AWS Strands Agents SDK (real `Agent` + tool-calling loop + `structured_output`) |
| **AWS services** | Amazon Bedrock **Nova** (reasoning), **Titan** embeddings (semantic search + RAG), **Polly** (voice); deployed on **Lambda + API Gateway + Function URL**, **S3 + CloudFront** |
| **Stack** | Python · FastAPI · Pydantic · pytest · React 19 · TypeScript · Vite · Tailwind |
| **License** | [MIT](LICENSE) |
| **Architecture** | [`docs/architecture.drawio`](docs/architecture.drawio) |

> Everything degrades gracefully: with no AWS credentials the same agent tools
> run in a deterministic pipeline, so the app always works. `GET /api/health`
> reports which path is live, honestly.

---

## How it works

A newcomer lands on a **chat page** and just talks to the Navigator. Based on
what they ask, the agent:

- **Explains** what re:Invent is and how to get started
- **Finds sessions** for a topic (from the real 1,500+ session catalog)
- **Gives prep advice** grounded in past-attendee tips (RAG)
- **Builds a route** — a full day-by-day plan, or three ranked options:
  **Plan A (ideal) / B (backup) / C (low-risk)**
- **Re-routes** when a session becomes full or cancelled, protecting the goal

## Agent Watch — runs in the background, pings you only on a decision

Once your route is built, Re:Route stops being an app you babysit. The
**autonomous monitor** (`app/engine/monitor.py`) watches your selected sessions
and, on each scan tick (a cron / Amazon EventBridge schedule in production, or
`POST /api/monitor/scan` in the demo), re-checks the route against changing
conditions — a session that just filled up or was cancelled, or a venue
transition that turned infeasible.

It stays quiet while the route is healthy. When something **changes** and needs a
human call, it opens a *decision* that already carries the pre-analyzed fix
(recommended replacement sessions via the recovery engine) and asks you to
approve or dismiss. That's the only moment you're pulled in — the "Agent Watch"
page shows the calm/green state and lights up only when a decision is pending.

Endpoints: `POST /api/monitor/watch` · `POST /api/monitor/scan` ·
`GET /api/monitor/status` · `POST /api/monitor/decision/{id}/resolve`.

Under the hood, specialized agent roles are surfaced in the UI:

| Role | Responsibility |
|------|----------------|
| 🧭 Navigator | Understands the goal, coordinates the others, explains changes |
| 🔎 Session Scout | Finds matching sessions, repeats and fallbacks |
| 🛣️ Route Planner | Resolves conflicts, scores learning vs. walking vs. risk |
| 🧭 Wayfinder | Venue-to-venue travel time and buffers |
| 🔄 Recovery Navigator | Reacts when a session is missed/full and re-routes |

---

## Project structure

```
reroute/
├── backend/                     # FastAPI + Strands agent + planning engine
│   ├── app/
│   │   ├── api.py               # FastAPI app + all /api endpoints
│   │   ├── models.py            # Pydantic response models (Plan, RerouteResult…)
│   │   ├── lambda_handler.py    # AWS Lambda entry point
│   │   ├── agent/               # Strands agent, Navigator, tool wrappers
│   │   ├── engine/              # chat, planning, semantic search, RAG, learning graph
│   │   └── providers/           # Data providers (catalog, embeddings, MCP, demo)
│   ├── data/                    # re:Invent session catalog + prep tips (RAG)
│   ├── scripts/                 # Catalog refresh utility
│   ├── tests/                   # pytest suite
│   └── requirements.txt
│
├── frontend/                    # React 19 + TypeScript + Vite + Tailwind
│   └── src/
│       ├── pages/               # Chat (landing), Mission, Plans, Sessions, Explore…
│       ├── components/          # ui/ kit, layout/ shell, agent/ activity
│       └── lib/                 # API client, mappers, mission store
│
├── infra/                       # AWS SAM / CloudFormation templates
│   ├── reroute-lambda.yaml      # Backend: Lambda + Function URL + API Gateway
│   └── reroute-frontend-hosting.yaml   # Frontend: S3 + CloudFront
│
└── docs/                        # Catalog export + MCP notes
```

---

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.api:app --reload --port 8000
```

The API runs at `http://localhost:8000` (interactive docs at `/docs`). It works
fully in demo mode with no AWS credentials.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173` and proxies `/api` to the backend on `:8000`.

### Tests

```bash
cd backend
python -m pytest -q
```

---

## Enabling live AWS services

All AWS features are off by default (deterministic mode). Turn them on with
environment variables plus AWS credentials that have Bedrock/Polly access.
`GET /api/aws/status` reports which services are live.

| Variable | Enables |
|----------|---------|
| `REROUTE_USE_STRANDS_MODEL=1` | Amazon Nova drives the Strands tool-calling loop |
| `REROUTE_USE_BEDROCK_EMBEDDINGS=1` | Amazon Titan embeddings for semantic search |
| `REROUTE_USE_POLLY=1` | Amazon Polly voice readout |
| `REROUTE_MODEL=nova-pro` | Model choice: `nova-premier` / `nova-pro` / `nova-lite` / `nova-micro` |
| `AWS_REGION=us-east-1` | A region with Bedrock model access enabled |

The models are Amazon-only (Nova family on Bedrock). `GET /api/health` reports
the active orchestrator (`strands-bedrock` or `deterministic-tools`) honestly.

---

## Session catalog

The app ships with the real re:Invent 2026 catalog at
`backend/data/reinvent2026_sessions.json` (loaded by default). To refresh it or
import your own export, see [`docs/GET_CATALOG.md`](docs/GET_CATALOG.md).

You can also serve sessions from the standalone
[`reinvent2026-mcp`](https://github.com/dineshrajdhanapathyDD/reinvent2026-mcp)
server over MCP — see [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md). Without it, the
bundled catalog is used.

---

## Deploy to AWS

Backend (Lambda + Function URL). Uses SAM; build in a container so native deps
resolve for the Lambda runtime:

```bash
cd infra
sam build --template reroute-lambda.yaml --use-container
sam deploy --region us-east-1 --stack-name reroute-ai --resolve-s3 \
  --capabilities CAPABILITY_IAM --no-confirm-changeset \
  --parameter-overrides "BedrockModel=nova-pro UseBedrockModel=1 UseBedrockEmbeddings=1 UsePolly=1"
```

Frontend (S3 + CloudFront). Point `frontend/.env.production` at the backend's
Function URL, then build and sync:

```bash
cd frontend
npm run build
aws s3 sync dist "s3://<your-site-bucket>" --delete --region us-east-1
aws cloudfront create-invalidation --distribution-id <your-dist-id> --paths "/*"
```

The frontend hosting stack (`infra/reroute-frontend-hosting.yaml`) provisions a
private S3 bucket, CloudFront with origin access control, and SPA routing.

---

## API highlights

| Endpoint | Purpose |
|----------|---------|
| `POST /api/chat` | Conversational entry point (intent → advice / sessions / plan) |
| `POST /api/plan` | Build a full route from a mission |
| `POST /api/plans/abc` | Three ranked plans: ideal / backup / low-risk |
| `POST /api/reroute` | Recover a route when a session is dropped |
| `POST /api/advice` | RAG preparation tips |
| `GET /api/catalog/filter` | Filter the full catalog by topic/level/format/venue/day |
| `GET /api/health` · `GET /api/aws/status` | Runtime + live-service status |

---

## License

Released under the [MIT License](LICENSE).

Built for AWS re:Invent 2026.
