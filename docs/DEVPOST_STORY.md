# Re:Route AI — Devpost Project Story

> Paste each section into the matching field on the Devpost submission form.
> Written in first person singular for a solo build — swap "I" → "we" if you have
> teammates.

**Project name:** Re:Route AI
**Elevator pitch:** An autonomous agent that plans your AWS re:Invent schedule and re-routes you in the background — pinging you only when a session fills up and a real decision is needed.
**Live demo:** https://d315hfgmfqehyn.cloudfront.net
**Repo:** https://github.com/dineshrajdhanapathyDD/reroute-2026

---

## Inspiration

I've watched people lose entire days at big conferences to one small, repeating
chore: rebuilding their schedule. AWS re:Invent is the extreme version — ~1,500
sessions across six Las Vegas venues, popular ones fill in minutes, and rooms can
be a 20-minute walk apart. You arrive with a real goal ("get production-ready with
AI agents") and spend the week reshuffling instead of learning. That's exactly the
"Agents for Humans" problem: a routine, judgment-heavy task that quietly drains
your time. I wanted an agent that does the busywork and only interrupts me when
there's a genuine decision to make.

## What it does

Re:Route AI turns a plain-language learning goal into a realistic, walkable
re:Invent route, then keeps that route alive in the background.

- **Talk to it.** You type a goal ("I'm new — build me a plan for learning GenAI")
  and the agent explains, finds matching sessions from the real 1,500+ catalog,
  gives prep advice grounded in real attendee tips (RAG), and builds a
  conflict-free daily schedule — or three ranked options: Plan A (ideal) /
  B (backup) / C (low-risk).
- **Agent Watch — the heart of it.** Once your plan exists, the agent stops being
  an app you babysit. It runs on a schedule, re-checking your route against
  changing conditions. It stays quiet while everything's healthy, and only
  surfaces when something changes — a session fills up, a transition becomes
  infeasible — arriving with the fix already worked out (ranked replacement
  sessions). You just approve or dismiss.
- **Extras:** real Google Maps walking directions between venues (Wayfinder), and
  "Read aloud" using Amazon Polly.

## How we built it

- **Agent:** a real `strands.Agent` (Strands Agents SDK) backed by a
  `BedrockModel`, driving a tool-calling loop over `@tool` functions (search
  sessions, check conflicts, estimate travel, recommend alternatives) and
  returning typed Pydantic models via `structured_output`.
- **AWS:** Amazon Bedrock **Nova** for reasoning, **Titan** embeddings for
  semantic search + a RAG knowledge base, **Amazon Polly** for voice.
- **Backend:** FastAPI on **AWS Lambda** (via Mangum) behind both a **Function
  URL** (no 30s cap, for the agent loop) and an **API Gateway HTTP API**.
- **Frontend:** React 19 + TypeScript + Vite + Tailwind, hosted on
  **S3 + CloudFront**.
- **Deployed with AWS SAM**, with a least-privilege IAM role scoped to just the
  Nova/Titan/Polly ARNs. Everything degrades gracefully: with no credentials, the
  same tools run in a deterministic pipeline, so the app always works.

## Challenges we ran into

- **The empty-plan trap:** the model sometimes returned a well-formed but *empty*
  structured plan — no error, just a blank UI. Fix: validate the content, not just
  the shape, and fall back to the deterministic pipeline.
- **The 30-second cliff:** API Gateway's 30s cap killed the Nova tool loop
  mid-plan. Added a Lambda Function URL (no cap) for the agent path.
- **A CORS ghost:** the Function URL's CORS *and* FastAPI's CORS both set the
  header, producing a duplicated, invalid one the browser rejected. Made FastAPI
  the single source on Lambda.
- **Reframing for the theme:** my first version was a great planner *you drove* —
  which isn't the brief. Adding Agent Watch (with a baseline snapshot so it pings
  on *changes*, not pre-existing conditions) is what turned it into a true
  background agent.

## Accomplishments that we're proud of

- A genuine Strands + Nova agent that does real end-to-end work, not a chatbot
  demo — and it's **live** on AWS.
- **Agent Watch:** an autonomous monitor that stays quiet and surfaces a
  *pre-analyzed* decision only when a human choice is truly needed. That's the
  "Agents for Humans" idea made real.
- It never breaks: deterministic fallback, honest `/api/health` reporting which
  path is live, and it works with zero credentials.
- Real data (the actual re:Invent catalog), real maps, and real voice.

## What we learned

- With structured LLM output, validate the *content*, not just the schema.
- The "surface only on a real decision" pattern is what separates a background
  agent from another app to manage — and the trick is snapshotting a baseline so
  you alert on *change*, not on the current state.
- Serverless choices matter: Function URL vs. API Gateway wasn't cosmetic — it
  decided whether the agent could finish at all.
- Designing for graceful degradation makes an agent demo-proof.

## What's next for Re:Route AI

- Per-user persistence for the monitor and a real **Amazon EventBridge** schedule
  for the background scan tick.
- Explore **Amazon Bedrock AgentCore** for the agent runtime.
- Generalize the monitor pattern beyond conferences — the "plan once → watch for
  change → surface a pre-analyzed decision" loop fits bill-pay, care scheduling,
  and volunteer logistics.

---

## Built with

`strands-agents` · `amazon-bedrock` · `amazon-nova` · `amazon-titan` ·
`amazon-polly` · `aws-lambda` · `amazon-api-gateway` · `amazon-s3` ·
`amazon-cloudfront` · `aws-sam` · `python` · `fastapi` · `pydantic` · `react` ·
`typescript` · `vite` · `tailwindcss`
