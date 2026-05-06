from __future__ import annotations

from ..core.bash import CmdResult, run_script
from ..core.embedded_scripts import run_embedded_script


class UpdateFlavor:
    VM = "vm"  # kör /var/scripts/{n,pp}.sh (hämtas från GitHub om saknas)
    CUSTOMER = "customer"  # kör inbyggda scriptmallar (de ni använder för kunder)


def update_nc(
    *,
    dry_run: bool = False,
    flavor: str = UpdateFlavor.CUSTOMER,
    debug: bool = False,
    keep_tmp: bool = False,
) -> CmdResult:
    args: list[str] = []
    if dry_run:
        args.append("--dry-run")
    if flavor == UpdateFlavor.VM:
        return run_script("n", args, sudo=True)
    env = {"DEBUG": "1"} if debug else None
    return run_embedded_script("n.sh", sudo=True, env=env, keep_tmp=keep_tmp)


def update_php(
    *,
    dry_run: bool = False,
    flavor: str = UpdateFlavor.CUSTOMER,
    phpver: str | None = None,
    keep_tmp: bool = False,
) -> CmdResult:
    args: list[str] = []
    if dry_run:
        args.append("--dry-run")
    if flavor == UpdateFlavor.VM:
        return run_script("pp", args, sudo=True)
    env = {"PHPVER": phpver} if phpver else None
    return run_embedded_script("pp.sh", sudo=True, env=env, keep_tmp=keep_tmp)

