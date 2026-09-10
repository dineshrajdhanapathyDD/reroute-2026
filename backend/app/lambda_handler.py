"""AWS Lambda entry point for the Re:Route AI FastAPI backend.

Wraps the existing FastAPI app with Mangum so the same app that runs under
uvicorn locally runs on Lambda behind API Gateway (HTTP API) — no code changes
to the app itself. Amazon-models-only (Bedrock Nova) keeps the runtime footprint
and IAM simple for a serverless hackathon deploy.

Deploy: see infra/reroute-lambda.yaml.
"""
from mangum import Mangum

from app.api import app

# API Gateway HTTP API ($default stage) -> Mangum -> FastAPI.
handler = Mangum(app, lifespan="off")
