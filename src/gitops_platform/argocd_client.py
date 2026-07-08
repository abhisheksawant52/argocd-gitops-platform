"""Thin client around the ArgoCD REST API.

The client wraps the subset of the ArgoCD API used by the control helper:
listing applications, reading sync/health status, and triggering syncs. Network
calls are made lazily via a :class:`requests.Session`; nothing connects at import
time, so the module is safe to import in tests and offline environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .config import Settings, get_settings
from .logging_config import get_logger

logger = get_logger("argocd_client")


class ArgoCDError(RuntimeError):
    """Raised when the ArgoCD API returns an error or is unreachable."""


@dataclass(frozen=True)
class ApplicationStatus:
    """Normalised view of an ArgoCD application's status."""

    name: str
    namespace: str
    sync_status: str
    health_status: str
    repo_url: str
    path: str
    target_revision: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "ApplicationStatus":
        """Build an :class:`ApplicationStatus` from a raw API payload."""
        metadata = payload.get("metadata", {})
        spec = payload.get("spec", {})
        source = spec.get("source", {})
        status = payload.get("status", {})
        return cls(
            name=metadata.get("name", "unknown"),
            namespace=spec.get("destination", {}).get("namespace", "unknown"),
            sync_status=status.get("sync", {}).get("status", "Unknown"),
            health_status=status.get("health", {}).get("status", "Unknown"),
            repo_url=source.get("repoURL", ""),
            path=source.get("path", ""),
            target_revision=source.get("targetRevision", "HEAD"),
        )

    @property
    def is_synced(self) -> bool:
        """Return ``True`` when the application is fully synced."""
        return self.sync_status == "Synced"

    @property
    def is_healthy(self) -> bool:
        """Return ``True`` when the application reports a healthy state."""
        return self.health_status == "Healthy"


class ArgoCDClient:
    """Client for the ArgoCD REST API.

    Args:
        settings: Optional settings override. Defaults to :func:`get_settings`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        """Return a lazily-initialised authenticated session."""
        if self._session is None:
            session = requests.Session()
            if self.settings.argocd_auth_token:
                session.headers["Authorization"] = f"Bearer {self.settings.argocd_auth_token}"
            session.headers["Content-Type"] = "application/json"
            session.verify = not self.settings.argocd_insecure
            self._session = session
        return self._session

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Issue an HTTP request against the ArgoCD API and return JSON."""
        url = f"{self.settings.base_url}{path}"
        logger.debug("%s %s", method, url)
        try:
            response = self.session.request(
                method, url, timeout=self.settings.argocd_timeout, **kwargs
            )
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network path
            raise ArgoCDError(f"ArgoCD API request failed: {exc}") from exc
        return response.json() if response.content else {}

    def list_applications(self, project: str | None = None) -> list[ApplicationStatus]:
        """List applications, optionally filtered by ArgoCD project."""
        params = {"projects": project} if project else None
        payload = self._request("GET", "/applications", params=params)
        items = payload.get("items") or []
        return [ApplicationStatus.from_api(item) for item in items]

    def get_application(self, name: str) -> ApplicationStatus:
        """Fetch a single application's normalised status."""
        payload = self._request("GET", f"/applications/{name}")
        return ApplicationStatus.from_api(payload)

    def sync_application(self, name: str, prune: bool = False) -> dict[str, Any]:
        """Trigger a sync operation for an application."""
        body: dict[str, Any] = {"prune": prune}
        logger.info("Triggering sync for application '%s' (prune=%s)", name, prune)
        return self._request("POST", f"/applications/{name}/sync", json=body)
