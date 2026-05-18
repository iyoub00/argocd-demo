# ArgoCD Demo POC

A minimal GitOps demo: Python FastAPI app deployed to a local `kind` cluster via ArgoCD.

## Prerequisites

Install these tools first:

```bash
# Docker Desktop (https://www.docker.com/products/docker-desktop/)

# kind
brew install kind

# kubectl
brew install kubectl

# ArgoCD CLI
brew install argocd
```

---

## Step 1 — Create the local cluster

```bash
kind create cluster --name argocd-demo
kubectl cluster-info --context kind-argocd-demo
```

---

## Step 2 — Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=available deployment -l app.kubernetes.io/name=argocd-server -n argocd --timeout=120s
```

---

## Step 3 — Access the ArgoCD UI

```bash
# Forward the ArgoCD UI to localhost:8080
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get the initial admin password (in a separate terminal)
argocd admin initial-password -n argocd

# Login via CLI
argocd login localhost:8080 --username admin --insecure
```

Open https://localhost:8080 in your browser (accept the self-signed cert).

---

## Step 4 — Build & push the Docker image

```bash
# Replace <your-dockerhub-username> with your Docker Hub username
export DOCKER_USER=<your-dockerhub-username>

cd app
docker build -t $DOCKER_USER/argocd-demo:1.0.0 .
docker push $DOCKER_USER/argocd-demo:1.0.0
```

Update `k8s/deployment.yaml` — replace `<your-dockerhub-username>` with your actual username.

---

## Step 5 — Push the repo to GitHub

```bash
cd /path/to/argocd-demo
git init
git add .
git commit -m "initial demo setup"

# Create a new GitHub repo named argocd-demo, then:
git remote add origin https://github.com/<your-github-username>/argocd-demo.git
git push -u origin main
```

Update `argocd/application.yaml` — replace `<your-github-username>` with your actual username.

---

## Step 6 — Register the ArgoCD Application

```bash
kubectl apply -f argocd/application.yaml
```

ArgoCD will immediately sync the `k8s/` folder from your GitHub repo into the cluster.

Check status:
```bash
argocd app get demo-app
argocd app list
```

---

## Step 7 — Demo the GitOps flow

**Scale up replicas** — edit `k8s/deployment.yaml`, change `replicas: 2` → `replicas: 3`, commit and push:

```bash
git add k8s/deployment.yaml
git commit -m "scale to 3 replicas"
git push
```

ArgoCD detects the change within ~3 minutes and applies it automatically. You can also trigger a manual sync:

```bash
argocd app sync demo-app
```

**Update the app version:**
1. Edit `app/main.py` → change `VERSION = "1.0.0"` to `"2.0.0"`
2. Build & push a new image: `docker build -t $DOCKER_USER/argocd-demo:2.0.0 . && docker push ...`
3. Edit `k8s/deployment.yaml` → change the image tag to `2.0.0`
4. Commit and push → watch ArgoCD roll out the update

---

## Verify the app is running

```bash
# Port-forward the app
kubectl port-forward svc/demo-app -n demo-app 9000:80

# Test it
curl http://localhost:9000/
curl http://localhost:9000/health
```

---

## Cleanup

```bash
kind delete cluster --name argocd-demo
```
