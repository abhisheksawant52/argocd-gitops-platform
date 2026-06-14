#!/usr/bin/env python3
"""ArgoCD Manager CLI - Production-ready CLI for managing ArgoCD applications."""

import os
import subprocess
import sys
from typing import Optional

import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

load_dotenv()

console = Console()

ARGOCD_SERVER = os.getenv("ARGOCD_SERVER", "localhost:8080")
ARGOCD_AUTH_TOKEN = os.getenv("ARGOCD_AUTH_TOKEN", "")
ARGOCD_INSECURE = os.getenv("ARGOCD_INSECURE", "true").lower() == "true"


def get_session() -> requests.Session:
    """Create an authenticated requests session for ArgoCD API."""
    session = requests.Session()
    if ARGOCD_AUTH_TOKEN:
        session.headers.update({"Authorization": f"Bearer {ARGOCD_AUTH_TOKEN}"})
    session.headers.update({"Content-Type": "application/json"})
    if ARGOCD_INSECURE:
        session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return session


def api_url(path: str) -> str:
    """Build ArgoCD API URL."""
    server = ARGOCD_SERVER.rstrip("/")
    if not server.startswith("http"):
        server = f"https://{server}"
    return f"{server}/api/v1{path}"


def handle_response(resp: requests.Response, success_msg: str = "OK") -> dict:
    """Handle API response with rich error output."""
    try:
        resp.raise_for_status()
        console.print(f"[green]✓[/green] {success_msg}")
        return resp.json() if resp.content else {}
    except requests.exceptions.HTTPError as e:
        try:
            err = resp.json()
            msg = err.get("message", str(e))
        except Exception:
            msg = str(e)
        console.print(f"[red]✗ API Error:[/red] {msg}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Connection failed:[/red] Cannot reach ArgoCD server at {ARGOCD_SERVER}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        console.print("[red]✗ Timeout:[/red] ArgoCD server did not respond in time")
        sys.exit(1)


@click.group()
@click.version_option(version="1.0.0", prog_name="argocd-manager")
def cli():
    """ArgoCD Manager - Manage your ArgoCD applications with ease.

    Configure via environment variables:
      ARGOCD_SERVER       ArgoCD server address (default: localhost:8080)
      ARGOCD_AUTH_TOKEN   ArgoCD API auth token
      ARGOCD_INSECURE     Skip TLS verification (default: true)
    """
    if not ARGOCD_AUTH_TOKEN and not any(cmd in sys.argv for cmd in ["install", "--help"]):
        console.print("[yellow]⚠ Warning:[/yellow] ARGOCD_AUTH_TOKEN is not set")


@cli.command()
@click.option("--namespace", "-n", default="argocd", show_default=True, help="Kubernetes namespace for ArgoCD")
@click.option("--version", default="stable", show_default=True, help="ArgoCD version to install (e.g. v2.9.3 or stable)")
@click.option("--wait/--no-wait", default=True, show_default=True, help="Wait for ArgoCD pods to be ready")
def install(namespace: str, version: str, wait: bool):
    """Install ArgoCD into the current Kubernetes cluster.

    Uses kubectl to apply the official ArgoCD install manifest.
    Ensure your kubeconfig is configured for the target cluster.

    Example:
      argocd-manager install --namespace argocd --version v2.9.3
    """
    console.print(Panel(f"[bold blue]Installing ArgoCD[/bold blue]\nNamespace: {namespace} | Version: {version}"))

    install_url = f"https://raw.githubusercontent.com/argoproj/argo-cd/{version}/manifests/install.yaml"

    steps = [
        (["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"],
         ["kubectl", "apply", "-f", "-"],
         f"Creating namespace '{namespace}'"),
        (None, ["kubectl", "apply", "-n", namespace, "-f", install_url],
         f"Applying ArgoCD manifests from {install_url}"),
    ]

    # Create namespace
    console.print(f"[cyan]→[/cyan] Creating namespace '{namespace}'...")
    result = subprocess.run(
        ["kubectl", "create", "namespace", namespace],
        capture_output=True, text=True
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        console.print(f"[red]✗[/red] {result.stderr.strip()}")
        sys.exit(1)
    console.print(f"[green]✓[/green] Namespace '{namespace}' ready")

    # Apply install manifest
    console.print(f"[cyan]→[/cyan] Applying ArgoCD install manifest...")
    result = subprocess.run(
        ["kubectl", "apply", "-n", namespace, "-f", install_url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        console.print(f"[red]✗ kubectl apply failed:[/red]\n{result.stderr.strip()}")
        sys.exit(1)
    console.print(f"[green]✓[/green] ArgoCD manifests applied")

    if wait:
        console.print("[cyan]→[/cyan] Waiting for ArgoCD server to be ready (timeout: 300s)...")
        result = subprocess.run(
            ["kubectl", "rollout", "status", "deployment/argocd-server",
             "-n", namespace, "--timeout=300s"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[yellow]⚠ Rollout may not be ready:[/yellow] {result.stderr.strip()}")
        else:
            console.print("[green]✓[/green] ArgoCD server is ready")

    # Print access instructions
    console.print(Panel(
        f"[bold green]ArgoCD installed successfully![/bold green]\n\n"
        f"[yellow]Access ArgoCD UI:[/yellow]\n"
        f"  kubectl port-forward svc/argocd-server -n {namespace} 8080:443\n\n"
        f"[yellow]Get initial admin password:[/yellow]\n"
        f"  kubectl -n {namespace} get secret argocd-initial-admin-secret "
        f"-o jsonpath=\"{{.data.password}}\" | base64 -d",
        title="Next Steps"
    ))


@cli.command("list-apps")
@click.option("--project", "-p", default=None, help="Filter by ArgoCD project")
@click.option("--namespace", "-n", default=None, help="Filter by target namespace")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", show_default=True)
def list_apps(project: Optional[str], namespace: Optional[str], output: str):
    """List all ArgoCD applications.

    Displays application name, sync status, health status, repo URL, and path.

    Example:
      argocd-manager list-apps
      argocd-manager list-apps --project my-project --output json
    """
    session = get_session()
    params = {}
    if project:
        params["projects"] = project
    if namespace:
        params["appNamespace"] = namespace

    resp = session.get(api_url("/applications"), params=params, timeout=30)
    data = handle_response(resp, "Applications retrieved")

    apps = data.get("items", [])
    if not apps:
        console.print("[yellow]No applications found[/yellow]")
        return

    if output == "json":
        import json
        click.echo(json.dumps(apps, indent=2))
        return
    elif output == "yaml":
        import yaml
        click.echo(yaml.dump(apps, default_flow_style=False))
        return

    table = Table(title=f"ArgoCD Applications ({len(apps)} total)", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Project", style="blue")
    table.add_column("Sync Status", style="white")
    table.add_column("Health", style="white")
    table.add_column("Namespace", style="white")
    table.add_column("Repo", style="white", max_width=50)
    table.add_column("Path", style="white")

    sync_colors = {"Synced": "green", "OutOfSync": "yellow", "Unknown": "red"}
    health_colors = {"Healthy": "green", "Degraded": "red", "Progressing": "yellow", "Suspended": "blue", "Missing": "red", "Unknown": "dim"}

    for app in apps:
        spec = app.get("spec", {})
        status = app.get("status", {})
        sync_status = status.get("sync", {}).get("status", "Unknown")
        health_status = status.get("health", {}).get("status", "Unknown")
        sc = sync_colors.get(sync_status, "white")
        hc = health_colors.get(health_status, "white")

        table.add_row(
            app.get("metadata", {}).get("name", ""),
            spec.get("project", "default"),
            f"[{sc}]{sync_status}[/{sc}]",
            f"[{hc}]{health_status}[/{hc}]",
            spec.get("destination", {}).get("namespace", ""),
            spec.get("source", {}).get("repoURL", ""),
            spec.get("source", {}).get("path", ""),
        )

    console.print(table)


@cli.command("sync-app")
@click.argument("app_name")
@click.option("--revision", "-r", default=None, help="Sync to a specific revision/branch/tag")
@click.option("--prune/--no-prune", default=False, show_default=True, help="Prune resources during sync")
@click.option("--dry-run/--no-dry-run", default=False, show_default=True, help="Perform a dry run")
@click.option("--force/--no-force", default=False, show_default=True, help="Force sync (replace resources)")
def sync_app(app_name: str, revision: Optional[str], prune: bool, dry_run: bool, force: bool):
    """Trigger a sync for an ArgoCD application.

    Example:
      argocd-manager sync-app my-app
      argocd-manager sync-app my-app --revision v1.2.0 --prune
    """
    session = get_session()

    payload = {
        "name": app_name,
        "prune": prune,
        "dryRun": dry_run,
        "strategy": {
            "apply": {"force": force}
        }
    }
    if revision:
        payload["revision"] = revision

    console.print(f"[cyan]→[/cyan] Syncing application '[bold]{app_name}[/bold]'...")
    if dry_run:
        console.print("[yellow]⚠ Dry run mode - no changes will be applied[/yellow]")

    resp = session.post(api_url(f"/applications/{app_name}/sync"), json=payload, timeout=60)
    data = handle_response(resp, f"Sync triggered for '{app_name}'")

    status = data.get("status", {})
    sync = status.get("sync", {})
    health = status.get("health", {})
    console.print(f"  Sync Status : [cyan]{sync.get('status', 'N/A')}[/cyan]")
    console.print(f"  Health      : [cyan]{health.get('status', 'N/A')}[/cyan]")
    console.print(f"  Revision    : [cyan]{sync.get('revision', 'N/A')}[/cyan]")


@cli.command("delete-app")
@click.argument("app_name")
@click.option("--cascade/--no-cascade", default=True, show_default=True, help="Cascade delete (remove deployed resources)")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt")
def delete_app(app_name: str, cascade: bool, yes: bool):
    """Delete an ArgoCD application.

    By default performs a cascade delete (removes all deployed K8s resources).
    Use --no-cascade to remove only the ArgoCD Application resource.

    Example:
      argocd-manager delete-app my-app
      argocd-manager delete-app my-app --no-cascade --yes
    """
    if not yes:
        cascade_warn = " and all its deployed Kubernetes resources" if cascade else ""
        click.confirm(
            f"Delete application '{app_name}'{cascade_warn}?",
            abort=True
        )

    session = get_session()
    params = {"cascade": str(cascade).lower()}

    console.print(f"[cyan]→[/cyan] Deleting application '[bold]{app_name}[/bold]'...")
    resp = session.delete(api_url(f"/applications/{app_name}"), params=params, timeout=30)
    handle_response(resp, f"Application '{app_name}' deleted successfully")


@cli.command("get-app-status")
@click.argument("app_name")
@click.option("--output", "-o", type=click.Choice(["table", "json", "yaml"]), default="table", show_default=True)
def get_app_status(app_name: str, output: str):
    """Get detailed status of an ArgoCD application.

    Shows sync status, health, resources, and recent events.

    Example:
      argocd-manager get-app-status my-app
      argocd-manager get-app-status my-app --output json
    """
    session = get_session()

    resp = session.get(api_url(f"/applications/{app_name}"), timeout=30)
    data = handle_response(resp, f"Status retrieved for '{app_name}'")

    if output == "json":
        import json
        click.echo(json.dumps(data, indent=2))
        return
    elif output == "yaml":
        import yaml
        click.echo(yaml.dump(data, default_flow_style=False))
        return

    metadata = data.get("metadata", {})
    spec = data.get("spec", {})
    status = data.get("status", {})
    sync = status.get("sync", {})
    health = status.get("health", {})
    source = spec.get("source", {})
    dest = spec.get("destination", {})

    console.print(Panel(f"[bold cyan]{app_name}[/bold cyan]", title="Application Details"))

    info_table = Table(show_header=False, box=None)
    info_table.add_column("Key", style="bold", width=20)
    info_table.add_column("Value")

    sync_color = {"Synced": "green", "OutOfSync": "yellow"}.get(sync.get("status", ""), "white")
    health_color = {"Healthy": "green", "Degraded": "red", "Progressing": "yellow"}.get(health.get("status", ""), "white")

    info_table.add_row("Project", spec.get("project", "default"))
    info_table.add_row("Sync Status", f"[{sync_color}]{sync.get('status', 'N/A')}[/{sync_color}]")
    info_table.add_row("Health", f"[{health_color}]{health.get('status', 'N/A')}[/{health_color}]")
    info_table.add_row("Revision", sync.get("revision", "N/A"))
    info_table.add_row("Repo URL", source.get("repoURL", "N/A"))
    info_table.add_row("Path", source.get("path", "N/A"))
    info_table.add_row("Target Branch", source.get("targetRevision", "HEAD"))
    info_table.add_row("Cluster", dest.get("server", dest.get("name", "N/A")))
    info_table.add_row("Namespace", dest.get("namespace", "N/A"))
    info_table.add_row("Created", metadata.get("creationTimestamp", "N/A"))

    console.print(info_table)

    # Resources table
    resources = status.get("resources", [])
    if resources:
        res_table = Table(title="Resources", show_header=True, header_style="bold blue")
        res_table.add_column("Kind", style="cyan")
        res_table.add_column("Name")
        res_table.add_column("Namespace")
        res_table.add_column("Sync", style="white")
        res_table.add_column("Health", style="white")

        for r in resources:
            sync_s = r.get("syncStatus", "")
            health_s = r.get("health", {}).get("status", "") if isinstance(r.get("health"), dict) else ""
            sc = {"Synced": "green", "OutOfSync": "yellow"}.get(sync_s, "white")
            hc = {"Healthy": "green", "Degraded": "red", "Progressing": "yellow"}.get(health_s, "white")
            res_table.add_row(
                r.get("kind", ""),
                r.get("name", ""),
                r.get("namespace", ""),
                f"[{sc}]{sync_s}[/{sc}]",
                f"[{hc}]{health_s}[/{hc}]" if health_s else "-"
            )
        console.print(res_table)

    # Operation state
    op = status.get("operationState", {})
    if op:
        op_phase = op.get("phase", "")
        op_msg = op.get("message", "")
        phase_color = {"Succeeded": "green", "Failed": "red", "Running": "yellow"}.get(op_phase, "white")
        console.print(f"\n[bold]Last Operation:[/bold] [{phase_color}]{op_phase}[/{phase_color}]")
        if op_msg:
            console.print(f"  {op_msg}")


@cli.command("create-app")
@click.argument("app_name")
@click.option("--repo", "-r", required=True, help="Git repository URL")
@click.option("--path", "-p", required=True, help="Path within the repo to the app manifests")
@click.option("--dest-server", default="https://kubernetes.default.svc", show_default=True, help="Destination cluster API server URL")
@click.option("--dest-namespace", "-n", required=True, help="Target Kubernetes namespace")
@click.option("--project", default="default", show_default=True, help="ArgoCD project")
@click.option("--revision", default="HEAD", show_default=True, help="Target revision (branch, tag, or commit)")
@click.option("--auto-sync/--no-auto-sync", default=True, show_default=True, help="Enable automatic sync")
@click.option("--prune/--no-prune", default=True, show_default=True, help="Enable pruning of removed resources")
@click.option("--self-heal/--no-self-heal", default=True, show_default=True, help="Enable self-healing")
def create_app(
    app_name: str, repo: str, path: str, dest_server: str,
    dest_namespace: str, project: str, revision: str,
    auto_sync: bool, prune: bool, self_heal: bool
):
    """Create a new ArgoCD application.

    Example:
      argocd-manager create-app my-app \\
        --repo https://github.com/org/repo \\
        --path kubernetes/my-app \\
        --dest-namespace my-app \\
        --revision main
    """
    session = get_session()

    app_manifest = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": app_name,
            "namespace": "argocd",
            "finalizers": ["resources-finalizer.argocd.argoproj.io"]
        },
        "spec": {
            "project": project,
            "source": {
                "repoURL": repo,
                "targetRevision": revision,
                "path": path
            },
            "destination": {
                "server": dest_server,
                "namespace": dest_namespace
            },
            "syncPolicy": {}
        }
    }

    if auto_sync:
        app_manifest["spec"]["syncPolicy"] = {
            "automated": {
                "prune": prune,
                "selfHeal": self_heal
            },
            "syncOptions": [
                "CreateNamespace=true",
                "PrunePropagationPolicy=foreground",
                "PruneLast=true"
            ],
            "retry": {
                "limit": 5,
                "backoff": {
                    "duration": "5s",
                    "factor": 2,
                    "maxDuration": "3m"
                }
            }
        }

    console.print(f"[cyan]→[/cyan] Creating application '[bold]{app_name}[/bold]'...")
    console.print(f"  Repo     : {repo}")
    console.print(f"  Path     : {path}")
    console.print(f"  Cluster  : {dest_server}")
    console.print(f"  Namespace: {dest_namespace}")
    console.print(f"  AutoSync : {'[green]enabled[/green]' if auto_sync else '[yellow]disabled[/yellow]'}")

    resp = session.post(api_url("/applications"), json=app_manifest, timeout=30)
    data = handle_response(resp, f"Application '{app_name}' created successfully")

    console.print(f"\n[bold green]✓ Application '{app_name}' created![/bold green]")
    console.print(f"  View status: argocd-manager get-app-status {app_name}")
    console.print(f"  Trigger sync: argocd-manager sync-app {app_name}")


if __name__ == "__main__":
    cli()