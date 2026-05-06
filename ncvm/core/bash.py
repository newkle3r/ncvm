from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..config import Settings, get_settings
from .console import console


@dataclass(frozen=True)
class CmdResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _run(cmd: Sequence[str], *, check: bool = False, capture: bool = True) -> CmdResult:
    p = subprocess.run(list(cmd), text=True, capture_output=capture)
    # När capture=False är stdout/stderr None och output går direkt till terminalen.
    res = CmdResult(list(cmd), p.returncode, p.stdout or "", p.stderr or "")
    if check and not res.ok:
        raise subprocess.CalledProcessError(res.returncode, res.cmd, output=res.stdout, stderr=res.stderr)
    return res


def _has_sudo() -> bool:
    return _run(["bash", "-lc", "command -v sudo >/dev/null 2>&1"]).ok


def require_root_or_sudo() -> None:
    if os.name == "nt":
        return
    if os.geteuid() == 0:
        return
    if not _has_sudo():
        raise SystemExit("Måste köras som root eller ha sudo installerat/konfigurerat.")


def _maybe_sudo(cmd: list[str], sudo: bool) -> list[str]:
    if not sudo or os.name == "nt":
        return cmd
    if os.geteuid() == 0:
        return cmd
    return ["sudo", *cmd]


def ensure_script(name: str, *, settings: Settings | None = None) -> Path:
    """
    Säkerställ att `<scripts_dir>/<name>.sh` finns.
    Om den saknas, hämtas den från GitHub (som Nextcloud VM gör).
    """
    st = settings or get_settings()
    scripts_dir = Path(st.scripts_dir)
    script_path = scripts_dir / f"{name}.sh"

    if script_path.exists():
        return script_path

    require_root_or_sudo()

    console.print(f"[yellow]Hämtar {name}.sh från GitHub...[/yellow]")
    url = f"{st.github_base.rstrip('/')}/{name}.sh"

    mkdir_cmd = _maybe_sudo(["mkdir", "-p", str(scripts_dir)], sudo=True)
    _run(mkdir_cmd, check=True)

    curl_cmd = _maybe_sudo(["curl", "-fsSL", url, "-o", str(script_path)], sudo=True)
    _run(curl_cmd, check=True)

    chmod_cmd = _maybe_sudo(["chmod", "+x", str(script_path)], sudo=True)
    _run(chmod_cmd, check=True)

    return script_path


def run_script(
    name: str,
    args: list[str] | None = None,
    *,
    sudo: bool = True,
    stream: bool = True,
) -> CmdResult:
    script = ensure_script(name)
    cmd = [str(script), *(args or [])]
    cmd = _maybe_sudo(cmd, sudo=sudo)
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")
    return _run(cmd, capture=not stream)


def run_bash(command: str, *, sudo: bool = True, stream: bool = True) -> CmdResult:
    """
    Kör ett bash-kommando via `bash -lc`.
    Används för att t.ex. `source`a `lib.sh` och anropa en funktion.
    """
    cmd = ["bash", "-lc", command]
    cmd = _maybe_sudo(cmd, sudo=sudo)
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")
    return _run(cmd, capture=not stream)


def source_lib_and_call(
    func_call: str,
    *,
    sudo: bool = True,
    settings: Settings | None = None,
    stream: bool = True,
) -> CmdResult:
    """
    Kör `source <(curl -sL .../lib.sh)` och anropar `func_call`.
    Exempel: func_call="calculate_php_fpm"
    """
    st = settings or get_settings()
    lib_local = Path(st.scripts_dir) / "lib.sh"
    if lib_local.exists():
        source_cmd = f"source {shlex.quote(str(lib_local))}"
    else:
        lib_url = f"{st.github_base.rstrip('/')}/lib.sh"
        source_cmd = f"source <(curl -fsSL {shlex.quote(lib_url)})"
    safe = f"set -euo pipefail; {source_cmd}; {func_call}"
    return run_bash(safe, sudo=sudo, stream=stream)

