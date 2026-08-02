# Architecture

The application is an on-demand troubleshooting system:

```text
Frontend
    -> FastAPI backend
    -> Kubernetes investigation layer (placeholder)
    -> AI Kubernetes agent (placeholder)
    -> LLM reasoning (placeholder)
    -> Diagnosis
```

An investigation will begin only after a user request. This project is not a Kubernetes controller or operator and does not run a continuous reconciliation loop.

## Current scope

- FastAPI application with `GET /health`
- Next.js application with backend health status
- Docker images and a local Compose stack
- Typed service and module boundaries for future work

Kubernetes access, LLM providers, authentication, and real-time updates are not implemented.

