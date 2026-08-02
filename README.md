# AI Kubernetes Troubleshooting Agent

An on-demand Kubernetes troubleshooting application. The FastAPI backend collects
pod, log, event, deployment, service, endpoint, and DNS evidence through `kubectl`,
then asks an OpenRouter-hosted model to return a structured root-cause diagnosis.

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
not be used. Provide the OpenRouter key supplied through InsForge and choose an
OpenRouter model in the same file:

```env
OPENROUTER_API_KEY=your-insforge-provided-key
OPENROUTER_MODEL=your-openrouter-model-id
```

Secrets are read only from the environment and must not be committed. Then collect
evidence and generate a diagnosis with:

```bash
curl -X POST http://localhost:8000/investigate \
  -H "Authorization: Bearer <insforge-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"<uuid>","namespace":"all"}'
```

The response keeps the raw `investigation` evidence and adds a structured
`diagnosis` with the root cause, explanation, fix, `kubectl` commands, prevention
recommendation, confidence score, and confidence reasoning. If OpenRouter is not
configured or is temporarily unavailable, the endpoint returns HTTP `503` without
exposing provider details or credentials.

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

### InsForge setup

1. Create an InsForge project and enable email/password authentication.
2. Run [`insforge/setup.sql`](insforge/setup.sql) in its SQL editor. This creates
   the history table, per-user row-level security, realtime channel, and progress
   trigger. Remove any prototype/public policies on `realtime.channels` before
   production so the included per-user subscription policy is authoritative.
3. Copy the project URL and anon key into `frontend/.env.local`:

   ```env
   NEXT_PUBLIC_INSFORGE_BASE_URL=https://your-project.region.insforge.app
   NEXT_PUBLIC_INSFORGE_ANON_KEY=your-anon-key
   ```

4. Add the same project URL to `backend/.env`:

   ```env
   INSFORGE_BASE_URL=https://your-project.region.insforge.app
   ```

The browser restores the InsForge session, subscribes to
`investigation:<user-id>`, and sends its access token to FastAPI. FastAPI verifies
that token with InsForge before running the existing investigation workflow. Each
collector transition updates the authenticated user's history record; the SQL
trigger publishes that update to the dashboard in realtime.

## Repository layout

```text
backend/    FastAPI application and Kubernetes investigation modules
frontend/   Next.js application
insforge/   InsForge table, RLS, channel, and realtime trigger setup
docs/       Architecture notes
prompts/    Project implementation prompts
```

See [docs/architecture.md](docs/architecture.md) for the current boundaries.
