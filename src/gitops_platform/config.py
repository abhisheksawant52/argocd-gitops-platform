"""Application configuration backed by environment variables.

Settings are loaded via ``pydantic-settings`` from the process environment and an
optional ``.env`` file. All values have safe local-development defaults so the
control helper can be imported without any external configuration.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the GitOps control helper.

    Environment variables are prefixed with ``ARGOCD_`` (for connection
    settings) and ``GITOPS_`` (for helper behaviour). See ``.env.example``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- ArgoCD connection -------------------------------------------------
    argocd_server: str = Field(
        default="localhost:8080",
        alias="ARGOCD_SERVER",
        description="ArgoCD API server host:port (without scheme).",
    )
    argocd_auth_token: str = Field(
        default="",
        alias="ARGOCD_AUTH_TOKEN",
        description="Bearer token used to authenticate against the ArgoCD API.",
    )
    argocd_insecure: bool = Field(
        default=True,
        alias="ARGOCD_INSECURE",
        description="Skip TLS verification (useful for local/self-signed setups).",
    )
    argocd_timeout: float = Field(
        default=30.0,
        alias="ARGOCD_TIMEOUT",
        description="Per-request timeout in seconds for ArgoCD API calls.",
    )

    # --- Helper behaviour --------------------------------------------------
    default_project: str = Field(
        default="platform",
        alias="GITOPS_DEFAULT_PROJECT",
        description="Default ArgoCD AppProject used when creating applications.",
    )
    sync_timeout: int = Field(
        default=300,
        alias="GITOPS_SYNC_TIMEOUT",
        description="Seconds to wait for an application to become healthy.",
    )
    log_level: str = Field(
        default="INFO",
        alias="GITOPS_LOG_LEVEL",
        description="Root log level (DEBUG, INFO, WARNING, ERROR).",
    )

    @property
    def base_url(self) -> str:
        """Return the fully-qualified ArgoCD API base URL."""
        scheme = "http" if self.argocd_insecure and ":8080" in self.argocd_server else "https"
        return f"{scheme}://{self.argocd_server}/api/v1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
