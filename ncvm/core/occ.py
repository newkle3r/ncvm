from __future__ import annotations

import json
import shlex
from dataclasses import dataclass

from ..config import get_settings
from .bash import CmdResult, _run, require_root_or_sudo
from .console import console


@dataclass(frozen=True)
class OccStatus:
    installed: bool | None
    versionstring: str | None
    maintenance: bool | None
    raw: str


def _sudo_u_www_php_occ(args: list[str]) -> CmdResult:
    st = get_settings()
    require_root_or_sudo()

    cmd = [
        "sudo",
        "-u",
        st.www_user,
        st.php_bin,
        st.occ_path,
        *args,
    ]
    console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")
    return _run(cmd, capture=True)


def occ(args: list[str]) -> CmdResult:
    """
    Primär väg: använd `/var/scripts/nextcloud_occ` om den finns (VM-standard).
    Fallback: `sudo -u www-data php /var/www/nextcloud/occ ...`
    """
    st = get_settings()
    from pathlib import Path

    script = Path(st.scripts_dir) / "nextcloud_occ"
    if script.exists():
        cmd = ["sudo", str(script), *args]
        console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")
        return _run(cmd, capture=True)

    return _sudo_u_www_php_occ(args)


def get_status() -> OccStatus:
    """
    Returnerar ett parsad statusobjekt.
    Försöker JSON först om `--output=json` stöds, annars text-parse.
    """
    res = occ(["status", "--output=json"])
    if res.ok:
        try:
            data = json.loads(res.stdout.strip() or "{}")
            return OccStatus(
                installed=data.get("installed"),
                versionstring=data.get("versionstring") or data.get("version"),
                maintenance=data.get("maintenance"),
                raw=res.stdout,
            )
        except Exception:
            pass

    res2 = occ(["status"])
    raw = (res2.stdout or "") + ("\n" + res2.stderr if res2.stderr else "")

    installed = None
    versionstring = None
    maintenance = None
    for line in raw.splitlines():
        s = line.strip()
        if s.lower().startswith("- installed:"):
            installed = s.split(":", 1)[1].strip().lower() == "true"
        if s.lower().startswith("- versionstring:"):
            versionstring = s.split(":", 1)[1].strip()
        if s.lower().startswith("- maintenance:"):
            maintenance = s.split(":", 1)[1].strip().lower() == "true"

    return OccStatus(installed=installed, versionstring=versionstring, maintenance=maintenance, raw=raw)

