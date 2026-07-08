"""Unit tests for the drift-detection logic."""

from gitops_platform.argocd_client import ApplicationStatus
from gitops_platform.drift import DriftSeverity, assess_application, detect_drift


def _app(name: str, sync: str, health: str) -> ApplicationStatus:
    return ApplicationStatus(
        name=name,
        namespace="default",
        sync_status=sync,
        health_status=health,
        repo_url="https://github.com/abhisheksawant52/argocd-gitops-platform",
        path="manifests/sample-nginx",
        target_revision="HEAD",
    )


def test_synced_healthy_app_has_no_drift():
    report = assess_application(_app("ok", "Synced", "Healthy"))
    assert report.severity is DriftSeverity.NONE
    assert not report.has_drift
    assert report.reasons == ()


def test_out_of_sync_is_critical():
    report = assess_application(_app("bad", "OutOfSync", "Healthy"))
    assert report.severity is DriftSeverity.CRITICAL
    assert report.has_drift
    assert any("sync status" in reason for reason in report.reasons)


def test_degraded_but_synced_is_warning():
    report = assess_application(_app("warn", "Synced", "Degraded"))
    assert report.severity is DriftSeverity.WARNING
    assert report.has_drift


def test_detect_drift_filters_healthy_apps():
    apps = [
        _app("a", "Synced", "Healthy"),
        _app("b", "OutOfSync", "Healthy"),
        _app("c", "Synced", "Progressing"),
    ]
    drifted = detect_drift(apps)
    assert {r.application for r in drifted} == {"b", "c"}
