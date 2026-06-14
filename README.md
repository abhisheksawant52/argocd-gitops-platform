# ArgoCD GitOps Platform

A production-ready **GitOps platform** built around ArgoCD. Manage Kubernetes application deployments declaratively - git is the source of truth.

## What's Included

- **ArgoCD Application manifests** - deploy apps via GitOps
- **Python CLI** (`argocd_manager.py`) - list, sync, create, and delete ArgoCD apps
- **Terraform** - install ArgoCD on any Kubernetes cluster via Helm
- **GitHub Actions** - validate manifests on PR, auto-sync on merge to main
- **Sample app** - nginx deployment managed by ArgoCD

---

## Quick Start

### 1. Install ArgoCD on your cluster

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Expose the server (LoadBalancer)
kubectl apply -f kubernetes/argocd-install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

### 2. Deploy ArgoCD with Terraform (alternative)

```bash
cd terraform
terraform init
terraform apply
terraform output port_forward_command   # access UI locally
terraform output get_initial_password_command
```

### 3. Deploy the sample app via ArgoCD

```bash
kubectl apply -f kubernetes/sample-app.yaml
```

ArgoCD will automatically sync and deploy `kubernetes/manifests/deployment.yaml` to the cluster.

### 4. Use the Python CLI

```bash
pip install -r src/requirements.txt
export ARGOCD_SERVER="localhost:8080"
export ARGOCD_AUTH_TOKEN="<your-token>"

python src/argocd_manager.py list-apps
python src/argocd_manager.py app-status --app sample-nginx-app
python src/argocd_manager.py sync-app --app sample-nginx-app
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| kubectl | 1.29+ | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| ArgoCD CLI | latest | [argo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/cli_installation/) |
| Terraform | 1.5+ | [hashicorp.com](https://developer.hashicorp.com/terraform/install) |
| Python | 3.11+ | [python.org](https://www.python.org) |
| Helm | 3.x | [helm.sh](https://helm.sh/docs/intro/install/) |

---

## Repository Structure

```
argocd-gitops-platform/
├── .github/workflows/gitops-sync.yml   # Validate + auto-sync on push
├── kubernetes/
│   ├── argocd-install.yaml             # LoadBalancer service for ArgoCD UI
│   ├── sample-app.yaml                 # ArgoCD Application CRD
│   └── manifests/
│       └── deployment.yaml             # The actual app manifests ArgoCD deploys
├── src/
│   ├── argocd_manager.py               # Python CLI
│   └── requirements.txt
├── terraform/
│   ├── main.tf                         # Install ArgoCD via Helm
│   ├── variables.tf
│   └── outputs.tf
└── README.md
```

---

## Python CLI Usage

Set environment variables:

```bash
export ARGOCD_SERVER="argocd.example.com:443"   # or localhost:8080 for port-forward
export ARGOCD_AUTH_TOKEN="<your-argocd-api-token>"
export ARGOCD_INSECURE="true"                    # set to false for production TLS
```

### Commands

#### `list-apps`
```bash
python src/argocd_manager.py list-apps
python src/argocd_manager.py list-apps --namespace production --output json
```

#### `app-status`
```bash
python src/argocd_manager.py app-status --app sample-nginx-app
```

#### `sync-app`
```bash
# Sync and wait for healthy
python src/argocd_manager.py sync-app --app sample-nginx-app

# Sync with pruning (removes stale resources)
python src/argocd_manager.py sync-app --app sample-nginx-app --prune
```

#### `create-app`
```bash
python src/argocd_manager.py create-app \
  --app my-new-app \
  --repo https://github.com/my-org/my-repo \
  --path helm/myapp \
  --dest-namespace production \
  --auto-sync \
  --self-heal
```

#### `delete-app`
```bash
python src/argocd_manager.py delete-app --app my-new-app --yes
```

---

## GitOps Workflow

```
Developer pushes to main
         |
         v
GitHub Actions validates manifests
         |
         v
ArgoCD detects git change
         |
         v
ArgoCD syncs to cluster (automated)
         |
         v
Health checks pass -> Deployed
```

Changes to `kubernetes/manifests/` trigger ArgoCD to reconcile the cluster state automatically.

---

## GitHub Actions

### Required Secrets

| Secret | Description |
|--------|-------------|
| `ARGOCD_SERVER` | ArgoCD server address (e.g. `argocd.example.com`) |
| `ARGOCD_AUTH_TOKEN` | ArgoCD API token |

### Workflow Behaviour

| Event | Action |
|-------|--------|
| PR to `main` | Validate manifests + Terraform plan |
| Push to `main` | Auto-sync ArgoCD application |
| Manual trigger | Sync specific app |

---

## Terraform

Installs ArgoCD on an existing Kubernetes cluster using the official Helm chart.

```bash
cd terraform
terraform init
terraform plan
terraform apply

# Get ArgoCD UI access
terraform output port_forward_command
# Run: kubectl port-forward svc/argocd-server -n argocd 8080:80
# Then open: http://localhost:8080

# Get initial password
terraform output get_initial_password_command
```

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `argocd_namespace` | `argocd` | Namespace to install ArgoCD |
| `argocd_helm_version` | `6.11.1` | Helm chart version |
| `argocd_image_tag` | `v2.11.3` | ArgoCD image tag |
| `argocd_service_type` | `LoadBalancer` | Service type for ArgoCD server |

---

## Cleanup

```bash
# Delete ArgoCD apps
kubectl delete -f kubernetes/sample-app.yaml
kubectl delete namespace sample-app

# Uninstall ArgoCD
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl delete namespace argocd

# Or via Terraform
cd terraform && terraform destroy
```

---

## Troubleshooting

**ArgoCD CLI returns "transport: Error while dialing"**
Check `ARGOCD_SERVER` is set correctly and the server is reachable. Use `kubectl port-forward` for local access.

**App stuck in OutOfSync**
Run `python src/argocd_manager.py sync-app --app <name> --prune` to reconcile.

**Helm Terraform providers not configured**
Uncomment the provider blocks in `terraform/main.tf` and point them to your kubeconfig or cluster credentials.
