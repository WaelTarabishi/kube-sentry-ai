# Architecture

The application is an on-demand troubleshooting system:

```text
Frontend
    -> FastAPI backend
    -> Kubernetes investigation layer (kubectl evidence collection)
    -> AI Kubernetes agent (placeholder)
    -> LLM reasoning (placeholder)
    -> Diagnosis
```

An investigation will begin only after a user request. This project is not a Kubernetes controller or operator and does not run a continuous reconciliation loop.

## Current scope

- FastAPI application with `GET /health` and `POST /investigate`
- Next.js application with backend health status
- Docker images and a local Compose stack
- Typed service and module boundaries for future work

The investigation layer invokes `kubectl` as a subprocess and gathers evidence only. LLM reasoning, authentication, recommendations, and real-time updates are not implemented.
