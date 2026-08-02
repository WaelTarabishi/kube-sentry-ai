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

- FastAPI application with `GET /health`, authenticated `GET /clusters`, and
  authenticated `POST /investigate`
- Next.js application with authentication, kubeconfig cluster selection, live
  progress, friendly error/empty states, diagnosis, and investigation history
- Docker images and a local Compose stack
- Structured root-cause, fix, prevention, and confidence output

The cluster endpoint reads every usable cluster/context pair from the backend's
kubeconfig. The selected context is validated with a short API-server preflight,
then the investigation layer invokes `kubectl --context <selected-context>` as a
subprocess and gathers evidence.
The AI layer treats that evidence as untrusted data, sends a deterministic prompt
to the configured OpenRouter model, and validates the returned JSON before exposing
it through the API. InsForge validates browser sessions, stores history, and
publishes collector progress to the authenticated user's realtime channel.

Intentional failure manifests under `k8s/failure-scenarios` provide an isolated,
repeatable lab for CrashLoopBackOff, ImagePullBackOff, OOMKilled, and Service
selector mismatch investigations.
