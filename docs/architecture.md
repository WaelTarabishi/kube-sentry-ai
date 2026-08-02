# Architecture

The application is an on-demand troubleshooting system:

```text
Frontend
    -> FastAPI backend
    -> Kubernetes investigation layer (kubectl evidence collection)
    -> AI Kubernetes agent
    -> OpenRouter LLM reasoning
    -> Structured diagnosis and suggested fix
```

An investigation will begin only after a user request. This project is not a Kubernetes controller or operator and does not run a continuous reconciliation loop.

## Current scope

- FastAPI application with `GET /health` and `POST /investigate`
- Next.js application with backend health status
- Docker images and a local Compose stack
- Structured root-cause, fix, prevention, and confidence output

The investigation layer invokes `kubectl` as a subprocess and gathers evidence.
The AI layer treats that evidence as untrusted data, sends a deterministic prompt
to the configured OpenRouter model, and validates the returned JSON before exposing
it through the API. Authentication, history, frontend investigation UI, deployment,
and real-time updates remain outside the current scope.
