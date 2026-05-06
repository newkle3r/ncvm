from __future__ import annotations

from ..core.console import console
from ..core.runner import RunError
from ..services.update_service import UpdateService


def run_update(
    target: str,
    *,
    phpver: str | None = None,
    dry_run: bool = False,
    skip_backup: bool = False,
    debug: bool = False,
) -> int:
    try:
        svc = UpdateService(debug=debug)
        target = target.lower().strip()
        if target == "nc":
            r = svc.update_nextcloud(dry_run=dry_run, skip_backup=skip_backup)
            return 0 if r.ok else 1
        if target == "php":
            r = svc.update_php(phpver=phpver, dry_run=dry_run)
            return 0 if r.ok else 1
        if target == "all":
            r = svc.update_all(phpver=phpver, dry_run=dry_run, skip_backup=skip_backup)
            return 0 if r.ok else 1
        console.print("[red]target måste vara nc, php eller all[/red]")
        return 2
    except RunError as e:
        console.print(f"[red]{e}[/red]")
        return e.returncode
    except Exception as e:
        console.print(f"[red]{type(e).__name__}: {e}[/red]")
        return 1
