# Testing Instructions — Re:Route AI

How to verify the agent's main features. No login or credentials required — the
live demo is public and free to use.

- **Live demo:** https://d315hfgmfqehyn.cloudfront.net
- **API base (Lambda Function URL):** https://ertldwrhpgsnbmg66muiftp73e0wskgr.lambda-url.us-east-1.on.aws

The fastest path is the **UI walkthrough** below. The **API checks** at the end
let you verify each capability directly.

---

## A. UI walkthrough (≈ 3 minutes, no setup)

Open the live demo. You land on the **Chat** page.

### 1. Talk to the agent (conversational planning)
- Type: **"I'm new — build me a plan for learning GenAI agents"**
- Expect: a friendly reply, then a **"View full plan in Mission Control"** button.
- Click it → **Mission** shows your goal, a journey score, and today's sessions.

### 2. See the real schedule (multi-day, real catalog)
- Go to **Schedule**. Click the day tabs (**Tuesday → Friday**).
- Expect: each day shows real sessions with times, venues, and match scores.

### 3. Three ranked plans (A / B / C)
- In Chat, type: **"Give me Plan A / B / C for learning GenAI"**
- Expect: three plan cards — **Ideal / Backup / Low-risk** — each with session
  count, journey score, and walking distance. "Use A/B/C" applies one.

### 4. Wayfinder (real maps)
- Go to **Wayfinder**, pick a session.
- Expect: **Directions** opens real Google Maps walking directions between venues;
  **Open venue** drops a pin on the real property.

### 5. Voice (Amazon Polly)
- On any Chat reply, click the 🔊 speaker button; or on **Mission**, click
  **Read plan**.
- Expect: the text is read aloud (Amazon Polly neural voice on the live demo;
  falls back to the browser voice otherwise).

### 6. ⭐ Agent Watch — the autonomous background agent (the main feature)
This shows the agent running quietly and surfacing only when a decision is needed.

1. Build a plan first (step 1 above), then open **Agent Watch**.
2. It shows **"Route healthy — nothing needs you"** and a live "Monitoring" pulse.
   This is the normal, quiet state.
3. Simulate a change: on the **Sessions** page note one session id, then mark it
   full (see the one-line command in step B.6 below), and back on **Agent Watch**
   click **Scan now**.
4. Expect: the agent raises **one decision** — what changed, why it needs you, and
   **ranked replacement sessions** with a recommended pick already chosen.
5. Click **Approve recommended** (or **Use this** on an option). The route updates
   and the banner returns to green. The item moves to **Handled**.

---

## B. API checks (direct verification)

Set the base URL once:

```bash
BASE=https://ertldwrhpgsnbmg66muiftp73e0wskgr.lambda-url.us-east-1.on.aws/api
```

### 1. Health / which orchestrator is live
```bash
curl "$BASE/health"
curl "$BASE/aws/status"
```
Expect JSON reporting the active orchestrator and which AWS services are live.

### 2. Conversational agent
```bash
curl -X POST "$BASE/chat" -H "Content-Type: application/json" \
  -d '{"message":"build me a plan for learning genai agents"}'
```
Expect a reply, an `intent`, and structured `data` (a plan with sessions).

### 3. Build a full plan
```bash
curl -X POST "$BASE/plan" -H "Content-Type: application/json" \
  -d '{"mission":"production-ready AI agents on AWS, Agents and Bedrock"}'
```
Expect a `Plan` with `sessions`, a multi-day `daily_schedule`, and `scores`.

### 4. Plan A / B / C
```bash
curl -X POST "$BASE/plans/abc" -H "Content-Type: application/json" \
  -d '{"mission":"learn GenAI agents"}'
```
Expect three plans (ideal / backup / low-risk) with a summary each.

### 5. RAG preparation advice
```bash
curl -X POST "$BASE/advice" -H "Content-Type: application/json" \
  -d '{"mission":"first-timer tips"}'
```
Expect grounded `tips` retrieved from the knowledge base.

### 6. ⭐ Autonomous monitor (Agent Watch) — full loop
```bash
# a) Build a plan and grab a few session ids (jq optional)
IDS=$(curl -s -X POST "$BASE/plan" -H "Content-Type: application/json" \
  -d '{"mission":"AI agents and Bedrock"}' | jq -c '[.sessions[0:6][].id]')

# b) Watch the plan
curl -X POST "$BASE/monitor/watch" -H "Content-Type: application/json" \
  -d "{\"selected_ids\": $IDS, \"learning_goal\": \"AI agents\"}"

# c) Scan while healthy — expect new_decisions: []
curl -X POST "$BASE/monitor/scan" -H "Content-Type: application/json" -d '{}'

# d) Simulate a session filling up (use one id from step a)
curl -X POST "$BASE/demo/availability" -H "Content-Type: application/json" \
  -d '{"session_id":"<one-of-those-ids>","status":"full"}'

# e) Scan again — now it raises ONE decision with ranked alternatives
curl -X POST "$BASE/monitor/scan" -H "Content-Type: application/json" -d '{}'

# f) See pending decisions
curl "$BASE/monitor/status"

# g) Resolve it (approve the recommended swap)
curl -X POST "$BASE/monitor/decision/<decision-id>/resolve" \
  -H "Content-Type: application/json" -d '{"action":"approve"}'
```
Expect: healthy scan returns no decisions; after the change, the scan raises a
single decision carrying pre-analyzed replacement options; resolving swaps the
session and returns the route to healthy.

### 7. Voice (Amazon Polly)
```bash
curl -X POST "$BASE/voice/speak" -H "Content-Type: application/json" \
  -d '{"text":"Testing Re Route voice."}' --output speak.mp3
```
Expect an MP3 file (Amazon Polly) when voice is enabled, or HTTP 204 (frontend
then uses the browser voice).

---

## C. Run and test locally (optional, zero AWS credentials)

```bash
# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.api:app --reload --port 8000     # docs at /docs

# Frontend (new terminal)
cd frontend
npm install
npm run dev                                            # http://localhost:5173

# Backend tests
cd backend
python -m pytest -q                                    # 78 passed, 1 skipped
```

Locally the agent runs a deterministic pipeline (the same tools, model-free), so
every feature above works without any AWS setup.
