# Architecture

The platform follows the ArgoCD **app-of-apps** pattern. Git is the single source
of truth; ArgoCD continuously reconciles the cluster to match the declared state.

## Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `platform` AppProject | `argocd/projects/platform.yaml` | Scopes allowed repos, clusters, and namespaces. |
| Root Application | `argocd/root-app.yaml` | Watches `argocd/applications/` and renders child apps. |
| Child Applications | `argocd/applications/` | One Application per workload (e.g. `sample-nginx`). |
| Workload manifests | `manifests/<app>/` | Deployment, Service, Ingress, HPA, NetworkPolicy, PDB. |
| Control plane install | `clusters/argocd/install.yaml` | Namespace + LoadBalancer service for ArgoCD. |
| Terraform | `terraform/` | Installs ArgoCD via the official Helm chart. |
| Control helper | `src/gitops_platform/` | CLI for status/sync/drift against the ArgoCD API. |

## Reconciliation loop

1. A developer merges a change to `main`.
2. ArgoCD detects the new git revision for each Application.
3. Applications with automated sync policy reconcile automatically; others are
   synced with the `gitops-platform` CLI or the ArgoCD UI.
4. Self-heal reverts any manual cluster drift back to the git-declared state.
5. The `gitops-platform drift` command reports any application whose live state
   no longer matches git (`OutOfSync` or non-`Healthy`).
