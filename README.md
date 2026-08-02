# AI Kubernetes Troubleshooting Agent

Foundation for an on-demand Kubernetes troubleshooting application. The FastAPI backend can collect pod, log, event, deployment, service, endpoint, and DNS evidence through `kubectl`. AI reasoning is intentionally not implemented yet.

## Run with Docker

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs

Stop the services with `docker compose down`.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env  # Windows
uvicorn app.main:app --reload
```

On macOS or Linux, use `cp .env.example .env` instead of `copy`.

The backend requires `kubectl` on its `PATH` and access to a cluster. Set
`KUBECONFIG_PATH` in `backend/.env` when the default kubectl configuration should
not be used. Then collect evidence with:

```bash
curl -X POST http://localhost:8000/investigate
```

The backend Docker image includes `kubectl`. When running it in a container,
mount a kubeconfig into the container and set `KUBECONFIG_PATH` to that in-container
path, or provide cluster credentials through your deployment environment.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local  # Windows
npm run dev
```

On macOS or Linux, use `cp .env.example .env.local`.

## Repository layout

```text
backend/    FastAPI application and Kubernetes investigation modules
frontend/   Next.js application
docs/       Architecture notes
prompts/    Project implementation prompts
```

See [docs/architecture.md](docs/architecture.md) for the current boundaries.
