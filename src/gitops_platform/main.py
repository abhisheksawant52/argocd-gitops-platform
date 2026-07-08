"""Command-line entrypoint for the ArgoCD GitOps control helper.

Provides a small operator-facing CLI to inspect application status, trigger
syncs, and report configuration drift across an ArgoCD instance.

Examples:
    gitops-platform status
    gitops-platform sync --app sample-nginx --prune
    gitops-platform drift --project platform
"""

from __future__ import annotations

import json

import click

from . import __version__
from .argocd_client import ArgoCDClient, ArgoCDError
from .config import get_settings
from .drift import detect_drift
from .logging_config import configure_logging
from .sync import SyncController


@click.group()
@click.version_option(__version__, prog_name="gitops-platform")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """ArgoCD GitOps control helper — sync, status, and drift detection."""
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx.ensure_object(dict)
    ctx.obj["client"] = ArgoCDClient(settings)


@cli.command("status")
@click.option("--project", "-p", default=None, help="Filter by ArgoCD project.")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def status(ctx: click.Context, project: str | None, output: str) -> None:
    """List applications with their sync and health status."""
    client: ArgoCDClient = ctx.obj["client"]
    try:
        apps = client.list_applications(project=project)
    except ArgoCDError as exc:
        raise click.ClickException(str(exc)) from exc

    if output == "json":
        click.echo(json.dumps([app.__dict__ for app in apps], indent=2))
        return

    if not apps:
        click.echo("No applications found.")
        return

    header = f"{'NAME':<24}{'SYNC':<14}{'HEALTH':<14}{'NAMESPACE'}"
    click.echo(header)
    for app in apps:
        click.echo(
            f"{app.name:<24}{app.sync_status:<14}{app.health_status:<14}{app.namespace}"
        )


@cli.command("sync")
@click.option("--app", "-a", "app_name", default=None, help="Application to sync.")
@click.option("--project", "-p", default=None, help="Sync all out-of-sync apps in a project.")
@click.option("--prune/--no-prune", default=False, help="Prune resources not in git.")
@click.pass_context
def sync(ctx: click.Context, app_name: str | None, project: str | None, prune: bool) -> None:
    """Trigger a sync for a single app or all out-of-sync apps in a project."""
    controller = SyncController(client=ctx.obj["client"])
    try:
        if app_name:
            result = controller.sync(app_name, prune=prune)
            click.echo(result.message)
        else:
            results = controller.sync_out_of_sync(project=project)
            if not results:
                click.echo("All applications are already synced.")
            for result in results:
                click.echo(result.message)
    except ArgoCDError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command("drift")
@click.option("--project", "-p", default=None, help="Filter by ArgoCD project.")
@click.pass_context
def drift(ctx: click.Context, project: str | None) -> None:
    """Report applications whose live state has drifted from git."""
    client: ArgoCDClient = ctx.obj["client"]
    try:
        apps = client.list_applications(project=project)
    except ArgoCDError as exc:
        raise click.ClickException(str(exc)) from exc

    reports = detect_drift(apps)
    if not reports:
        click.echo("No drift detected. All applications match git.")
        return

    for report in reports:
        click.echo(f"[{report.severity.value.upper()}] {report.application}")
        for reason in report.reasons:
            click.echo(f"  - {reason}")
    raise SystemExit(1)


def main() -> None:
    """Console-script entrypoint."""
    cli(obj={})


if __name__ == "__main__":
    main()
