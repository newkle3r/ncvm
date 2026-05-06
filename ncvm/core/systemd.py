from __future__ import annotations

import shlex

from .bash import CmdResult, _run, require_root_or_sudo
from .console import console


def systemctl(args: list[str]) -> CmdResult:
    require_root_or_sudo()
    cmd = ["sudo", "systemctl", *args]
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")
    return _run(cmd, capture=True)


def is_active(service: str) -> bool:
    res = systemctl(["is-active", "--quiet", service])
    return res.returncode == 0

