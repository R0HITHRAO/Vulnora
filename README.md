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

## Safety boundary

Only test systems for which the operator has explicit authorization. The API
contract requires a signed authorization scope before a scan can be created.
Do not use this project to probe arbitrary public systems.
