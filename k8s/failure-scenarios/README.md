# Kubernetes failure lab

These manifests intentionally create broken workloads in the isolated
`k8s-agent-failure-lab` namespace. Use a disposable local or development cluster,
not production.

## Run one scenario

Replace `<context>` with a context shown in the application's cluster selector.

```bash
kubectl --context <context> apply -f k8s/failure-scenarios/namespace.yaml
kubectl --context <context> apply -f k8s/failure-scenarios/crashloop-missing-env.yaml
```

Wait until the failure is visible:

```bash
kubectl --context <context> get pods -n k8s-agent-failure-lab -w
```

Open the application, click the same cluster, and click **Investigate Cluster**.
The expected diagnosis is:

| Manifest | Kubernetes signal | Expected root cause | Expected fix |
| --- | --- | --- | --- |
| `crashloop-missing-env.yaml` | `CrashLoopBackOff` and a missing `DATABASE_URL` log | Required environment variable is missing | Add the value from a Secret or ConfigMap |
| `image-pull-backoff.yaml` | `ImagePullBackOff` / `ErrImagePull` | The image tag does not exist | Update the Deployment image |
| `oom-killed.yaml` | `OOMKilled` with a 32Mi limit | Container exceeded its memory limit | Increase memory requests/limits or reduce usage |
| `service-selector-mismatch.yaml` | Service has no matching pods/endpoints | Selector does not match pod labels | Change the Service selector to `app: selector-demo` |

Apply a different manifest after each test so the AI can identify one clear root
cause at a time. If several scenarios run together, the response intentionally
chooses only the most likely primary cause.

## Clean up

This removes only the dedicated test namespace and everything created inside it:

```bash
kubectl --context <context> delete namespace k8s-agent-failure-lab
```
