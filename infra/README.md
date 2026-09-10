# Re:Route AI — AWS integration (CloudFormation)

`reroute-aws-integration.yaml` provisions **least-privilege IAM** for the AWS
services Re:Route AI uses:

- **Amazon Bedrock** — `InvokeModel` for the agent (Amazon Nova) and Titan Text
  Embeddings (semantic search + RAG), plus inference-profile discovery.
- **Amazon Polly** — `SynthesizeSpeech` (text-to-speech).

It creates a **managed policy**, an **application role** (attach to ECS/EC2/Lambda),
and — only if you ask — an **IAM user + access key** for local development.

> This template grants IAM. Deploy with `--capabilities CAPABILITY_NAMED_IAM`.
> It does **not** grant Bedrock *model access* — enable the models you plan to use
> in the Bedrock console (Model access) for your region first.

---

## Deploy

### Option A — application role (recommended for real deployments)

```bash
aws cloudformation deploy \
  --stack-name reroute-ai \
  --template-file infra/reroute-aws-integration.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides AppTrustService=ecs-tasks.amazonaws.com
```

Then attach the output `AppRoleArn` to your ECS task role / EC2 instance profile /
Lambda execution role. The backend picks up credentials automatically — just set
the feature toggles (below).

### Option B — IAM user with access keys (quick local dev)

```bash
aws cloudformation deploy \
  --stack-name reroute-ai-dev \
  --template-file infra/reroute-aws-integration.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides CreateDevUser=true
```

Read the access keys from the stack outputs (they are shown once):

```bash
aws cloudformation describe-stacks --stack-name reroute-ai-dev \
  --query "Stacks[0].Outputs" --output table
```

> The secret key is a stack output — retrieve it, put it in your local env, then
> consider deleting the stack or rotating the key. Never commit it.

---

## Wire it into the backend

Set AWS credentials (from the role, or the dev user keys) and turn on the
services (see `backend/.env.example`):

```powershell
$env:AWS_REGION="us-west-2"
# If using the dev user from Option B:
# $env:AWS_ACCESS_KEY_ID="<DevAccessKeyId>"
# $env:AWS_SECRET_ACCESS_KEY="<DevSecretAccessKey>"

$env:REROUTE_USE_STRANDS_MODEL="1"        # Bedrock agent (Amazon Nova)
$env:REROUTE_MODEL="nova-pro"
$env:REROUTE_USE_BEDROCK_EMBEDDINGS="1"   # Titan embeddings
$env:REROUTE_USE_POLLY="1"                # Polly voice

cd backend
python -m uvicorn app.api:app --port 8000
```

Verify: `GET /api/aws/status` should show each service flip to **live**, and the
Mission Control **AWS Integration** panel reflects it.

---

## Serverless deploy — AWS Lambda (recommended for the hackathon)

`reroute-lambda.yaml` deploys the FastAPI backend as a **Lambda function** with
both a **Function URL** (no 30s cap — used by the frontend so the Nova agent loop
can finish) and an **API Gateway HTTP API** (for fast endpoints). It uses
**Amazon models only** (Bedrock Nova + Titan embeddings) and Amazon Polly. The
Lambda's execution role is scoped to those Amazon model ARNs — no extra services.

Build in a container (`--use-container`) so native dependencies resolve for the
Lambda runtime.

The FastAPI app runs unchanged on Lambda via the Mangum adapter
(`backend/app/lambda_handler.py`). The bundled 1,507-session catalog is packaged
with the function, so it works without the MCP subprocess.

### Deploy with AWS SAM

```bash
# from the infra/ folder (samconfig.toml + template are here)
cd infra
sam build --template reroute-lambda.yaml
sam deploy --guided        # first time; then just `sam deploy`
```

SAM installs `backend/requirements.txt` (including `mangum`) into the package.
On success it prints `ApiUrl` and `HealthUrl` outputs. Point the frontend's
`/api` proxy (or `VITE` base) at `ApiUrl`.

Toggle Amazon services with the template parameters (all default on):
`BedrockModel` (nova-premier|nova-pro|nova-lite|nova-micro), `UseBedrockModel`,
`UseBedrockEmbeddings`, `UsePolly`.

> Enable the chosen Nova model + Titan embeddings under Bedrock → Model access
> for your region before invoking.

### Verify the deploy

```bash
curl "$(aws cloudformation describe-stacks --stack-name reroute-ai \
  --query "Stacks[0].Outputs[?OutputKey=='HealthUrl'].OutputValue" --output text)"
```

---

## Least-privilege notes

- The policy scopes Bedrock `InvokeModel` to Amazon Nova and Titan-embed ARNs
  only (foundation models + `us.` cross-region inference profiles) — not `*`.
- Polly is limited to `SynthesizeSpeech` / `DescribeVoices`.
- Discovery actions (`ListFoundationModels`, `GetInferenceProfile`) use `*`
  resource because they don't support resource-level scoping.
- Prefer the **role** path (Option A). Use the dev user only for local testing
  and clean it up afterward.

## Tear down

```bash
aws cloudformation delete-stack --stack-name reroute-ai       # or reroute-ai-dev
```
