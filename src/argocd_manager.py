"""
ArgoCD GitOps Platform Manager — CLI for managing ArgoCD applications and sync status.

Usage:
    python argocd_manager.py list-apps
    python argocd_manager.py sync-app --app my-app
    python argocd_manager.py app-status --app my-app
    python argocd_manager.py create-app --app my-app --repo https://github.com/org/repo --path helm/myapp --dest-namespace default
    python argocd_manager.py delete-app --app my-app
"""

import json
import logging
import os
import subprocess
import sys
from typing import Optional

import click
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("argocd-manager")


def _argocd_cmd(args: list, capture: bool = True) -> tuple[int, str, str]:
    """Run an argocd CLI command."""
    server = os.environ.get("ARGOCD_SERVER", "localhost:8080")
    token = os.environ.get("ARGOCD_AUTH_TOKEN", "")

    base = ["argocd"] + args + ["--server", server]
    if token:
        base += ["--auth-token", token]

    # Disable TLS verification for local/dev setups (override with ARGOCD_INSECURE=false)
    if os.environ.get("ARGOCD_INSECURE", "true").lower() == "true":
        base += ["--insecure"]

    try:
        result = subprocess.run(base, capture_output=capture, text=True, timeout=60)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 1, "", "argocd CLI not found. Install from https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out."


def _require_argocd():
    rc, _, _ = _argocd_cmd(["version", "--client"])
    if rc != 0:
        raise click.ClickException(
            "argocd CLI not found or not accessible.\n"
            "Install: https://argo-cd.readthedocs.io/en/stable/cli_installation/\n"
            "Set ARGOCD_SERVER and ARGOCD_AUTH_TOKEN environment variables."
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.version_option("1.0.0", prog_name="argocd-manager")
def cli():
    """ArgoCD GitOps Platform Manager — manage ArgoCD applications from the CLI."""


@cli.command("list-apps")
@click.option("--namespace", "-n", default=None, help="Filter by destination namespace.")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", show_default=True)
def list_apps(namespace: Optional[str], output: str):
    """List all ArgoCD applications.

    \b
    Example:
        python argocd_manager.py list-apps
        python argocd_manager.py list-apps --output json
    """
    _require_argocd()

    args = ["app", "list", "--output", "json"]
    rc, stdout, stderr = _argocd_cmd(args)

    if rc != 0:
        raise click.ClickException(f"Failed to list apps: {stderr}")

    try:
        apps = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        apps = []

    if namespace:
        apps = [a for a in apps if a.get("spec", {}).get("destination", {}).get("namespace") == namespace]

    if not apps:
        click.echo("No ArgoCD applications found.")
        return

    if output == "json":
        click.echo(json.dumps(apps, indent=2))
    else:
        rows = []
        for app in apps:
            spec = app.get("spec", {})
            status = app.get("status", {})
            rows.append({
                "Name": app.get("metadata", {}).get("name", "\u2014"),
                "Namespace": spec.get("destination", {}).get("namespace", "\u2014"),
                "Sync Status": status.get("sync", {}).get("status", "\u2014"),
                "Health": status.get("health", {}).get("status", "\u2014"),
                "Repo": spec.get("source", {}).get("repoURL", "\u2014")[:50],
                "Path": spec.get("source", {}).get("path", "\u2014"),
            })
        click.echo(tabulate(rows, headers="keys", tablefmt="rounded_outline"))


@cli.command("app-status")
@click.option("--app", "-a", required=True, help="Application name.")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", show_default=True)
def app_status(app: str, output: str):
    """Show the sync and health status of an ArgoCD application.

    \b
    Example:
        python argocd_manager.py app-status --app my-app
    """
    _require_argocd()

    rc, stdout, stderr = _argocd_cmd(["app", "get", app, "--output", "json"])

    if rc != 0:
        raise click.ClickException(f"Failed to get app '{app}': {stderr}")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise click.ClickException("Failed to parse ArgoCD response.")

    if output == "json":
        click.echo(json.dumps(data, indent=2))
        return

    status = data.get("status", {})
    sync = status.get("sync", {})
    health = status.get("health", {})
    spec = data.get("spec", {})
    source = spec.get("source", {})

    sync_status = sync.get("status", "\u2014")
    health_status = health.get("status", "\u2014")

    sync_color = {"Synced": "green", "OutOfSync": "yellow", "Unknown": "white"}.get(sync_status, "white")
    health_color = {"Healthy": "green", "Degraded": "red", "Progressing": "yellow"}.get(health_status, "white")

    rows = [
        {"Field": "Name", "Value": data.get("metadata", {}).get("name", "\u2014")},
        {"Field": "Sync Status", "Value": click.style(sync_status, fg=sync_color)},
        {"Field": "Health", "Value": click.style(health_status, fg=health_color)},
        {"Field": "Repo", "Value": source.get("repoURL", "\u2014")},
        {"Field": "Path", "Value": source.get("path", "\u2014")},
        {"Field": "Target Revision", "Value": source.get("targetRevision", "HEAD")},
        {"Field": "Destination Namespace", "Value": spec.get("destination", {}).get("namespace", "\u2014")},
        {"Field": "Sync Policy", "Value": "Automated" if spec.get("syncPolicy", {}).get("automated") else "Manual"},
    ]
    click.echo(tabulate(rows, headers="keys", tablefmt="rounded_outline"))

    resources = status.get("resources", [])
    if resources:
        click.echo(f"\nResources ({len(resources)}):")
        res_rows = []
        for r in resources[:20]:
            h = r.get("health", {}).get("status", "\u2014")
            color = {"Healthy": "green", "Degraded": "red"}.get(h, "white")
            res_rows.append({
                "Kind": r.get("kind", "\u2014"),
                "Name": r.get("name", "\u2014"),
                "Namespace": r.get("namespace", "\u2014"),
                "Status": r.get("status", "\u2014"),
                "Health": click.style(h, fg=color),
            })
        click.echo(tabulate(res_rows, headers="keys", tablefmt="simple"))


@cli.command("sync-app")
@click.option("--app", "-a", required=True, help="Application name.")
@click.option("--prune/--no-prune", default=False, show_default=True, help="Prune resources not in git.")
@click.option("--force/--no-force", default=False, show_default=True, help="Force sync even if already synced.")
@click.option("--wait/--no-wait", default=True, show_default=True, help="Wait for sync to complete.")
def sync_app(app: str, prune: bool, force: bool, wait: bool):
    """Trigger a sync for an ArgoCD application.

    \b
    Example:
        python argocd_manager.py sync-app --app my-app --prune
    """
    _require_argocd()

    args = ["app", "sync", app]
    if prune:
        args.append("--prune")
    if force:
        args.append("--force")

    logger.info("Syncing application '%s'...", app)
    rc, stdout, stderr = _argocd_cmd(args)

    if rc != 0:
        raise click.ClickException(f"Sync failed for '{app}': {stderr}")

    click.echo(click.style(f"\u2713 Application '{app}' sync initiated.", fg="green"))

    if wait:
        logger.info("Waiting for application to be healthy...")
        rc, stdout, stderr = _argocd_cmd(["app", "wait", app, "--health", "--timeout", "300"])
        if rc != 0:
            click.echo(click.style(f"\u26a0 Application '{app}' did not reach healthy state: {stderr}", fg="yellow"))
        else:
            click.echo(click.style(f"\u2713 Application '{app}' is healthy.", fg="green"))


@cli.command("create-app")
@click.option("--app", "-a", required=True, help="Application name.")
@click.option("--repo", required=True, help="Git repository URL.")
@click.option("--path", required=True, help="Path within the repo to the manifests/helm chart.")
@click.option("--dest-namespace", default="default", show_default=True, help="Destination Kubernetes namespace.")
@click.option("--dest-server", default="https://kubernetes.default.svc", show_default=True)
@click.option("--revision", default="HEAD", show_default=True, help="Git branch/tag/commit.")
@click.option("--auto-sync/--no-auto-sync", default=True, show_default=True, help="Enable automated sync.")
@click.option("--self-heal/--no-self-heal", default=True, show_default=True, help="Enable self-healing.")
@click.option("--project", default="default", show_default=True, help="ArgoCD project.")
def create_app(app, repo, path, dest_namespace, dest_server, revision, auto_sync, self_heal, project):
    """Create a new ArgoCD application.

    \b
    Example:
        python argocd_manager.py create-app \\
            --app my-app \\
            --repo https://github.com/org/repo \\
            --path helm/myapp \\
            --dest-namespace production
    """
    _require_argocd()

    args = [
        "app", "create", app,
        "--repo", repo,
        "--path", path,
        "--dest-server", dest_server,
        "--dest-namespace", dest_namespace,
        "--revision", revision,
        "--project", project,
    ]

    if auto_sync:
        args += ["--sync-policy", "automated"]
    if self_heal:
        args += ["--self-heal"]

    logger.info("Creating ArgoCD application '%s'...", app)
    rc, stdout, stderr = _argocd_cmd(args)

    if rc != 0:
        raise click.ClickException(f"Failed to create app '{app}': {stderr}")

    click.echo(click.style(f"\u2713 Application '{app}' created successfully.", fg="green"))


@cli.command("delete-app")
@click.option("--app", "-a", required=True, help="Application name.")
@click.option("--cascade/--no-cascade", default=True, show_default=True, help="Delete Kubernetes resources too.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete_app(app: str, cascade: bool, yes: bool):
    """Delete an ArgoCD application.

    \b
    Example:
        python argocd_manager.py delete-app --app my-app --yes
    """
    if not yes:
        click.confirm(f"Delete application '{app}'?", abort=True)

    _require_argocd()

    args = ["app", "delete", app, "--yes"]
    if not cascade:
        args += ["--cascade=false"]

    rc, stdout, stderr = _argocd_cmd(args)

    if rc != 0:
        raise click.ClickException(f"Failed to delete app '{app}': {stderr}")

    click.echo(click.style(f"\u2713 Application '{app}' deleted.", fg="green"))


if __name__ == "__main__":
    cli()
