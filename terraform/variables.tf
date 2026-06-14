variable "argocd_namespace" {
  description = "Kubernetes namespace for ArgoCD."
  type        = string
  default     = "argocd"
}

variable "argocd_helm_version" {
  description = "Version of the argo-cd Helm chart."
  type        = string
  default     = "6.11.1"
}

variable "argocd_image_tag" {
  description = "ArgoCD container image tag."
  type        = string
  default     = "v2.11.3"
}

variable "argocd_service_type" {
  description = "Service type for ArgoCD server (LoadBalancer, ClusterIP, NodePort)."
  type        = string
  default     = "LoadBalancer"
}
