from __future__ import annotations

import json
import logging

import typer
from rich import print as rprint
from rich.pretty import Pretty

from . import __version__
from .commands.doctor import run_doctor
from .commands.maintenance import maintenance_off, maintenance_on
from .commands.php_fpm import optimize_php_fpm
from .commands.restart import restart_webserver
from .commands.status import get_full_status
from .commands.update import run_update
from .core.console import console
from .core.runner import RunError

app = typer.Typer(
    help="Nextcloud VM Service CLI (Python-tjänster, ingen bash-orchestrering).",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main_callback(
    version: bool = typer.Option(False, "--version", help="Visa ncvm-version och avsluta."),
):
    if version:
        rprint(__version__)
        raise typer.Exit(0)


@app.command("update")
def update_cmd(
    target: str = typer.Argument(..., help="nc | php | all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skriv vad som skulle göras utan att köra."),
    phpver: str | None = typer.Option(
        None,
        "--phpver",
        help="PHP-version för update php / all (standard från config, t.ex. 8.3).",
    ),
    skip_backup: bool = typer.Option(
        False,
        "--skip-backup",
        help="Hoppa över rsync-backup av config+apps före Nextcloud-uppgradering.",
    ),
    skip_apps_backup: bool = typer.Option(
        False,
        "--skip-apps-backup",
        help="Backa bara upp config (hoppa över apps/) före Nextcloud-uppgradering.",
    ),
    debug: bool = typer.Option(False, "--debug", help="Verbose loggning (DEBUG)."),
):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    code = run_update(
        target,
        phpver=phpver,
        dry_run=dry_run,
        skip_backup=skip_backup,
        skip_apps_backup=skip_apps_backup,
        debug=debug,
    )
    raise typer.Exit(code)


@app.command("status")
def status_cmd(
    as_json: bool = typer.Option(False, "--json", help="Skriv status som JSON."),
):
    status = get_full_status()
    if as_json:
        rprint(json.dumps(status, ensure_ascii=False, indent=2))
        raise typer.Exit(0)
    rprint(Pretty(status, expand_all=True))


@app.command("maintenance")
def maintenance_cmd(
    mode: str = typer.Argument(..., help="on | off"),
):
    mode = mode.lower().strip()
    if mode == "on":
        raise typer.Exit(maintenance_on())
    if mode == "off":
        raise typer.Exit(maintenance_off())
    raise typer.BadParameter("mode måste vara: on | off")


@app.command("restart")
def restart_cmd():
    try:
        restart_webserver()
    except RunError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(e.returncode)


php_fpm_app = typer.Typer(help="PHP-FPM verktyg", no_args_is_help=True)
app.add_typer(php_fpm_app, name="php-fpm")


@php_fpm_app.command("optimize")
def php_fpm_optimize_cmd():
    try:
        optimize_php_fpm()
    except RunError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(e.returncode)


@app.command("doctor")
def doctor_cmd(
    as_json: bool = typer.Option(False, "--json", help="Skriv rapport som JSON."),
):
    out = run_doctor(as_json=as_json)
    rprint(out)


def main():
    app()


if __name__ == "__main__":
    main()
