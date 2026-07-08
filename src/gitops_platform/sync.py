"""High-level sync orchestration built on top of :class:`ArgoCDClient`."""

from __future__ import annotations

from dataclasses import dataclass

from .argocd_client import ApplicationStatus, ArgoCDClient
from .logging_config import get_logger

logger = get_logger("sync")


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a sync attempt for a single application."""

    application: str
    triggered: bool
    message: str


class SyncController:
    """Coordinates sync operations across one or more applications.

    Args:
        client: Optional pre-built :class:`ArgoCDClient`. A default client is
            created when omitted.
    """

    def __init__(self, client: ArgoCDClient | None = None) -> None:
        self.client = client or ArgoCDClient()

    def sync(self, name: str, prune: bool = False) -> SyncResult:
        """Trigger a sync for one application and return the result."""
        self.client.sync_application(name, prune=prune)
        return SyncResult(
            application=name,
            triggered=True,
            message=f"Sync triggered for '{name}' (prune={prune})",
        )

    def sync_out_of_sync(self, project: str | None = None) -> list[SyncResult]:
        """Sync every application that is not currently ``Synced``.

        Returns a :class:`SyncResult` for each application that was triggered.
        """
        apps: list[ApplicationStatus] = self.client.list_applications(project=project)
        results: list[SyncResult] = []
        for app in apps:
            if not app.is_synced:
                logger.info("Application '%s' is %s; syncing", app.name, app.sync_status)
                results.append(self.sync(app.name))
        return results
