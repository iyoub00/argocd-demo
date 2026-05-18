# How ArgoCD Works in This Project

## The Core Idea: Git as the Source of Truth

ArgoCD is a **GitOps continuous delivery tool** for Kubernetes. The principle is simple:

> Whatever is in the Git repository is what should be running in the cluster. ArgoCD's job is to make sure they always match.

Instead of running `kubectl apply` manually every time you want to deploy a change, you push to Git and ArgoCD takes care of the rest.

---

## The Flow

```
Developer → Git Push → GitHub Repo → ArgoCD detects diff → kubectl apply → Kubernetes
```

1. You edit a Kubernetes manifest (e.g. change the number of replicas or the image tag)
2. You commit and push to GitHub
3. ArgoCD polls the repo every ~3 minutes (or you trigger a manual sync)
4. ArgoCD compares what's in Git with what's running in the cluster
5. If there's a difference, ArgoCD applies the changes automatically

---

## Project Structure and What Each Part Does

```
argocd-demo/
├── app/                      # The application source code
│   ├── main.py               # FastAPI app with / and /health endpoints
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Builds the container image
│
├── k8s/                      # Kubernetes manifests — ArgoCD watches this folder
│   ├── namespace.yaml        # Creates the demo-app namespace
│   ├── deployment.yaml       # Runs 3 replicas of the app container
│   └── service.yaml          # Exposes the app inside the cluster on port 80
│
└── argocd/
    └── application.yaml      # Tells ArgoCD what repo/path/cluster to watch
```

**ArgoCD only watches the `k8s/` folder.** The `app/` folder is not deployed by ArgoCD — it is used to build the Docker image separately and push it to Docker Hub. ArgoCD then pulls that image via the tag specified in `k8s/deployment.yaml`.

---

## The ArgoCD Application Manifest

`argocd/application.yaml` is the key config that connects everything:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app
  namespace: argocd
spec:
  project: default

  source:
    repoURL: https://github.com/iyoub00/argocd-demo  # Git repo to watch
    targetRevision: HEAD                              # Always track the latest commit
    path: k8s                                         # Only sync this folder

  destination:
    server: https://kubernetes.default.svc            # The local cluster
    namespace: demo-app                               # Deploy into this namespace

  syncPolicy:
    automated:
      prune: true     # Delete resources that are removed from Git
      selfHeal: true  # Revert any manual changes made directly in the cluster
    syncOptions:
      - CreateNamespace=true  # Auto-create the namespace if it doesn't exist
```

Key settings explained:

| Setting | What it does |
|---|---|
| `automated` | ArgoCD syncs automatically without needing a manual trigger |
| `prune: true` | If you delete a manifest from Git, ArgoCD deletes it from the cluster too |
| `selfHeal: true` | If someone runs `kubectl edit` directly in the cluster, ArgoCD reverts it back to what Git says |
| `CreateNamespace=true` | ArgoCD creates the `demo-app` namespace automatically on first sync |

---

## What Happens on First Sync

When you run `kubectl apply -f argocd/application.yaml`:

1. ArgoCD registers the application
2. It clones `https://github.com/iyoub00/argocd-demo`
3. It reads all YAML files under `k8s/`
4. It applies them to the cluster in the right order (Namespace → Service → Deployment)
5. It continuously monitors both the repo and the cluster for drift

---

## Demo 1: Scale the App via GitOps

**Step 1** — Edit `k8s/deployment.yaml` and change `replicas`:

```yaml
spec:
  replicas: 3   # was 2
```

**Step 2** — Commit and push:

```bash
git add k8s/deployment.yaml
git commit -m "scale to 3 replicas"
git push
```

**Step 3** — Sync (or wait ~3 min for auto-sync):

```bash
argocd app sync demo-app --insecure
```

**Step 4** — Verify:

```bash
kubectl get pods -n demo-app
# You will see 3 running pods
```

ArgoCD applied the change without you ever touching `kubectl apply`.

---

## Demo 2: Deploy a New App Version

**Step 1** — Edit `app/main.py`:

```python
VERSION = "2.0.0"
```

**Step 2** — Build and push a new image:

```bash
cd app
podman build -t iyoub00/argocd-demo:2.0.0 .
podman push iyoub00/argocd-demo:2.0.0 docker.io/iyoub00/argocd-demo:2.0.0
```

**Step 3** — Update the image tag in `k8s/deployment.yaml`:

```yaml
image: iyoub00/argocd-demo:2.0.0
```

**Step 4** — Commit, push, and sync:

```bash
git add k8s/deployment.yaml
git commit -m "bump to v2.0.0"
git push
argocd app sync demo-app --insecure
```

**Step 5** — Verify the rollout:

```bash
kubectl get pods -n demo-app
curl http://localhost:9000/
# {"message":"Hello from ArgoCD demo!","version":"2.0.0"}
```

---

## Demo 3: Self-Healing in Action

With `selfHeal: true`, ArgoCD reverts any manual cluster changes back to what Git says.

Try manually scaling down the deployment:

```bash
kubectl scale deployment demo-app -n demo-app --replicas=1
kubectl get pods -n demo-app   # only 1 pod
```

Wait ~1 minute — ArgoCD detects the drift and restores it back to 3 replicas automatically.

```bash
kubectl get pods -n demo-app   # back to 3 pods
```

This demonstrates why **Git is the only place you should make changes** in a GitOps workflow.
