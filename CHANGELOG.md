# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-08

### Added

- `gitops-platform` CLI control helper with `status`, `sync`, and `drift` commands.
- ArgoCD API client, sync orchestration, and configuration drift detection modules.
- App-of-apps ArgoCD layout: root Application, `platform` AppProject, and a
  `sample-nginx` child Application.
- Production-grade Kubernetes manifests for the sample workload (namespace,
  service account, deployment, service, ingress, HPA, NetworkPolicy, PDB).
- Terraform module to install ArgoCD via the official Helm chart.
- Multi-stage, non-root Dockerfile with a healthcheck.
- Documentation, CI pipeline, pre-commit hooks, and open-source project files.
