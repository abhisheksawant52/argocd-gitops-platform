"""Configuration drift detection for ArgoCD-managed applications.

Drift is defined as any application whose live cluster state no longer matches
the desired state declared in git — i.e. an ``OutOfSync`` sync status or a
non-``Healthy`` health status. The functions here are pure and operate on
:class:`~gitops_platform.argocd_client.ApplicationStatus` objects so they can be
unit-tested without a live ArgoCD instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .argocd_client import ApplicationStatus
from .logging_config import get_logger

logger = get_logger("drift")


class DriftSeverity(str, Enum):
    """Severity classification for a drift finding."""

    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DriftReport:
    """A single application's drift assessment."""

    application: str
    sync_status: str
    health_status: str
    severity: DriftSeverity
    reasons: tuple[str, ...]

    @property
    def has_drift(self) -> bool:
        """Return ``True`` when any drift was detected."""
        return self.severity is not DriftSeverity.NONE


def assess_application(app: ApplicationStatus) -> DriftReport:
    """Assess a single application for configuration drift.

    ``OutOfSync`` is treated as critical drift (live state diverged from git);
    a degraded/unknown health with an otherwise-synced app is a warning.
    """
    reasons: list[str] = []
    severity = DriftSeverity.NONE

    if not app.is_synced:
        reasons.append(f"sync status is '{app.sync_status}' (expected 'Synced')")
        severity = DriftSeverity.CRITICAL

    if not app.is_healthy:
        reasons.append(f"health status is '{app.health_status}' (expected 'Healthy')")
        if severity is DriftSeverity.NONE:
            severity = DriftSeverity.WARNING

    return DriftReport(
        application=app.name,
        sync_status=app.sync_status,
        health_status=app.health_status,
        severity=severity,
        reasons=tuple(reasons),
    )


def detect_drift(apps: list[ApplicationStatus]) -> list[DriftReport]:
    """Return drift reports for every application that has drifted."""
    reports = [assess_application(app) for app in apps]
    drifted = [r for r in reports if r.has_drift]
    logger.info("Assessed %d applications; %d drifted", len(apps), len(drifted))
    return drifted
