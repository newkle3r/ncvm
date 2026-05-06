from __future__ import annotations

import os
import shlex
from importlib import resources

from .bash import CmdResult, _run, require_root_or_sudo
from .console import console


def _resource_text(relpath: str) -> str:
    # relpath t.ex. "pp.sh" i paketet ncvm.scripts
    return resources.files("ncvm.scripts").joinpath(relpath).read_text(encoding="utf-8")


def run_embedded_script(
    relpath: str,
    *,
    sudo: bool = True,
    env: dict[str, str] | None = None,
    keep_tmp: bool = False,
) -> CmdResult:
    """
    Skriver en inbyggd script-mall till `/tmp/ncvm-<name>.sh`, chmod +x, kör den.
    Avsedd att köras på Ubuntu/VM:n (inte på Windows).
    """
    if os.name == "nt":
        raise SystemExit("Detta kommando är avsett att köras på Ubuntu/Nextcloud VM, inte på Windows.")

    require_root_or_sudo()

    name = relpath.replace("/", "_")
    tmp_path = f"/tmp/ncvm-{name}"
    content = _resource_text(relpath)

    # Skriv filen på målet
    # Vi använder python -c för att undvika quoting-problem med heredoc via subprocess list.
    py = (
        "import pathlib; p=pathlib.Path(%r); p.write_text(%r, encoding='utf-8')"
        % (tmp_path, content)
    )
    cmd_write = ["sudo", "python3", "-c", py] if sudo else ["python3", "-c", py]
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd_write)}")
    res_write = _run(cmd_write, capture=True)
    if res_write.returncode != 0:
        return res_write

    cmd_chmod = ["sudo", "chmod", "+x", tmp_path] if sudo else ["chmod", "+x", tmp_path]
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd_chmod)}")
    res_chmod = _run(cmd_chmod, capture=True)
    if res_chmod.returncode != 0:
        return res_chmod

    # Kör med env-injektion
    env_part = ""
    if env:
        # export KEY=...; export ...
        exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        env_part = f"export {exports}; "

    # shell=True undviks; vi kör bash -lc
    cmd_run = ["sudo", "bash", "-lc", f"set -e; {env_part}bash {shlex.quote(tmp_path)}"] if sudo else [
        "bash",
        "-lc",
        f"set -e; {env_part}bash {shlex.quote(tmp_path)}",
    ]
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd_run)}")
    # Streama output så användaren ser allt i realtid
    res = _run(cmd_run, capture=False)

    if not keep_tmp:
        cmd_rm = ["sudo", "rm", "-f", tmp_path] if sudo else ["rm", "-f", tmp_path]
        console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd_rm)}")
        _run(cmd_rm, capture=True)

    return res

