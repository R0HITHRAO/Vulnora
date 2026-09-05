# Vulnora

Vulnora is an authorization-first security testing platform for LLM applications,
RAG pipelines, and AI agents. It combines reproducible security tests with an
interactive 3D security map.

## MVP scope

- Register an explicitly authorized target.
- Create a bounded scan with request and concurrency limits.
- Execute a safe demo scan and query its findings through the API.
- Visualize the target, attack paths, and findings in 3D.
- Keep scan state and findings behind a FastAPI boundary.
- Map findings to OWASP GenAI LLM Top 10 categories.

The 3D view is an operational visualization: every attack path should eventually
correspond to a real scan execution and evidence record.

## Repository layout

```text
apps/web       React + TypeScript + React Three Fiber frontend
apps/api       FastAPI backend
workers        Reserved for isolated scan workers
test_catalog   Versioned security-test definitions
```

## Local development

Prerequisites:

- Node.js 20+
- Python 3.12+
- Docker Desktop

```powershell
docker compose up -d postgres redis

cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ..\web
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and the API at
`http://localhost:8000/docs`.

Click **Run authorized demo scan** in the frontend after both services are
running. The backend currently stores scan records in memory and returns
deterministic demo findings; the next implementation phase will replace that
executor with isolated workers, a persistent database, and real target adapters.

### Amazon Bedrock target

Scans use the offline mock adapter by default. To assess an authorized Bedrock
model, set the adapter and credentials in the API process environment:

```powershell
$env:VULNORA_TARGET_ADAPTER = "bedrock"
$env:AWS_REGION = "us-east-1"
$env:BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
$env:AWS_BEARER_TOKEN_BEDROCK = "your-replacement-token"
```

The bearer token is read at runtime and is never stored in the database or
returned by the API. Use a new token if a previous token was exposed.

For NVIDIA-hosted Nemotron, use the NVIDIA API key separately:

```powershell
$env:VULNORA_TARGET_ADAPTER = "nvidia"
$env:NVIDIA_MODEL_ID = "nvidia/nemotron-3-super-120b-a12b"
$env:NVIDIA_API_KEY = "your-nvidia-api-key"
```

The NVIDIA adapter calls the OpenAI-compatible
`https://integrate.api.nvidia.com/v1/chat/completions` endpoint. Do not put an
NVIDIA key in `AWS_BEARER_TOKEN_BEDROCK`.

Create a scan only for an explicitly authorized target. The target hostname
must be included in `allowed_hostnames`; for NVIDIA-hosted inference, a minimal
request can use `https://integrate.api.nvidia.com` as the target URL:

```json
{
  "target": {
    "name": "Authorized NVIDIA Nemotron",
    "target_type": "chatbot",
    "base_url": "https://integrate.api.nvidia.com",
    "environment": "development"
  },
  "authorization": {
    "signed_by": "your-name",
    "allowed_hostnames": ["integrate.api.nvidia.com"],
    "approved_categories": ["prompt_injection", "disclosure", "agency"],
    "max_requests": 10,
    "max_concurrency": 1,
    "emergency_stop_contact": "your-email@example.com",
    "expires_at": "2026-12-31T23:59:59Z"
  },
  "categories": ["prompt_injection", "disclosure"],
  "safe_test_mode": false
}
```

## Safety boundary

Only test systems for which the operator has explicit authorization. The API
contract requires a signed authorization scope before a scan can be created.
Do not use this project to probe arbitrary public systems.
