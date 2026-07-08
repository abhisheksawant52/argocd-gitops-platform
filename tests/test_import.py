"""Smoke tests: the package and its modules import cleanly."""

import gitops_platform
from gitops_platform.argocd_client import ApplicationStatus, ArgoCDClient
from gitops_platform.config import Settings, get_settings


def test_version_exposed():
    assert isinstance(gitops_platform.__version__, str)
    assert gitops_platform.__version__.count(".") == 2


def test_settings_defaults():
    settings = Settings()
    assert settings.argocd_server
    assert settings.default_project == "platform"
    assert settings.base_url.endswith("/api/v1")


def test_client_is_lazy():
    # Constructing the client must not open a network connection.
    client = ArgoCDClient(get_settings())
    assert client.settings.default_project == "platform"


def test_application_status_from_api():
    app = ApplicationStatus.from_api(
        {
            "metadata": {"name": "demo"},
            "spec": {
                "destination": {"namespace": "demo-ns"},
                "source": {"repoURL": "https://example.com", "path": "manifests"},
            },
            "status": {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}},
        }
    )
    assert app.name == "demo"
    assert app.is_synced
    assert app.is_healthy
