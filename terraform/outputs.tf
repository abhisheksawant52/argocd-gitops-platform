output "argocd_namespace" {
  description = "Kubernetes namespace where ArgoCD is installed."
  value       = kubernetes_namespace.argocd.metadata[0].name
}

output "argocd_helm_release_name" {
  description = "Helm release name for ArgoCD."
  value       = helm_release.argocd.name
}

output "argocd_version" {
  description = "ArgoCD Helm chart version deployed."
  value       = helm_release.argocd.version
}

output "get_initial_password_command" {
  description = "Command to get the initial ArgoCD admin password."
  value       = "kubectl -n ${var.argocd_namespace} get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}

output "port_forward_command" {
  description = "Command to access ArgoCD UI locally."
  value       = "kubectl port-forward svc/argocd-server -n ${var.argocd_namespace} 8080:80"
}
