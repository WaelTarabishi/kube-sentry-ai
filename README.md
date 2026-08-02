# AI Kubernetes Troubleshooting Agent

Foundation for an on-demand Kubernetes troubleshooting application. The current implementation includes a FastAPI health service, a Next.js interface, environment templates, and Docker configuration. Kubernetes inspection and AI reasoning are intentionally left as placeholders.

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
backend/    FastAPI application and future investigation modules
frontend/   Next.js application
docs/       Architecture notes
prompts/    Project implementation prompts
```

See [docs/architecture.md](docs/architecture.md) for the current boundaries.

