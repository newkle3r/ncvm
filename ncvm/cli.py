from __future__ import annotations

import json

import typer
from rich import print as rprint
from rich.pretty import Pretty

from .commands.doctor import run_doctor
from .commands.maintenance import maintenance_off, maintenance_on
from .commands.php_fpm import optimize_php_fpm
from .commands.restart import restart_webserver
from .commands.status import get_full_status
from .commands.update import UpdateFlavor, update_nc, update_php
from .core.console import console

app = typer.Typer(
    help="Nextcloud VM Service CLI (orchestrerar lib.sh/n.sh/pp.sh).",
    no_args_is_help=True,
)


@app.command("update")
def update_cmd(
    target: str = typer.Argument(..., help="nc | php | all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skicka --dry-run till bash-skript om det stöds."),
    flavor: str = typer.Option(
        UpdateFlavor.CUSTOMER,
        "--flavor",
        help="Vilken metodik som ska användas: customer (inbyggda pp/n) eller vm (/var/scripts pp/n).",
    ),
    phpver: str | None = typer.Option(
        None,
        "--phpver",
        help="Överstyr PHPVER när --flavor customer och target=php/all (t.ex. 8.3).",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Sätt DEBUG=1 för customer-flavor (motsvarar lib.sh debug_mode).",
    ),
    keep_tmp: bool = typer.Option(
        False,
        "--keep-tmp",
        help="Behåll temporära scripts i /tmp på VM:n för felsökning.",
    ),
):
    target = target.lower().strip()
    if target not in {"nc", "php", "all"}:
        raise typer.BadParameter("target måste vara: nc | php | all")
    flavor = flavor.lower().strip()
    if flavor not in {UpdateFlavor.CUSTOMER, UpdateFlavor.VM}:
        raise typer.BadParameter("flavor måste vara: customer | vm")

    if target in {"nc", "all"}:
        console.print("[bold green]→ Uppdaterar Nextcloud/server (n.sh)[/bold green]")
        res = update_nc(dry_run=dry_run, flavor=flavor, debug=debug, keep_tmp=keep_tmp)
        if res.stdout:
            rprint(res.stdout)
        if res.stderr:
            console.print(f"[red]{res.stderr}[/red]")
        if res.returncode != 0:
            raise typer.Exit(res.returncode)

    if target in {"php", "all"}:
        console.print("[bold green]→ Uppdaterar PHP (pp.sh)[/bold green]")
        res = update_php(dry_run=dry_run, flavor=flavor, phpver=phpver, keep_tmp=keep_tmp)
        if res.stdout:
            rprint(res.stdout)
        if res.stderr:
            console.print(f"[red]{res.stderr}[/red]")
        if res.returncode != 0:
            raise typer.Exit(res.returncode)


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
    res = restart_webserver()
    if res.stdout:
        rprint(res.stdout)
    if res.stderr:
        console.print(f"[red]{res.stderr}[/red]")
    raise typer.Exit(res.returncode)


php_fpm_app = typer.Typer(help="PHP-FPM verktyg", no_args_is_help=True)
app.add_typer(php_fpm_app, name="php-fpm")


@php_fpm_app.command("optimize")
def php_fpm_optimize_cmd():
    res = optimize_php_fpm()
    if res.stdout:
        rprint(res.stdout)
    if res.stderr:
        console.print(f"[red]{res.stderr}[/red]")
    raise typer.Exit(res.returncode)


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

