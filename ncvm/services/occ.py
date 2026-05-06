from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner


@dataclass(frozen=True)
class OccStatus:
    installed: bool | None
    versionstring: str | None
    maintenance: bool | None
    raw: str


class NextcloudOcc:
    """Wrapper runt Nextcloud OCC (motsvarar nextcloud_occ / sudo -u www-data php occ)."""

    def __init__(self, runner: ProcessRunner, settings: Settings | None = None):
        self.runner = runner
        self.settings = settings or get_settings()

    def _script_path(self) -> Path | None:
        p = Path(self.settings.scripts_dir) / "nextcloud_occ"
        return p if p.exists() else None

    def _base_cmd(self) -> list[str]:
        script = self._script_path()
        if script:
            if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
                return [str(script)]
            return ["sudo", str(script)]
        return [
            "sudo",
            "-u",
            self.settings.www_user,
            self.settings.php_bin,
            self.settings.occ_path,
        ]

    def run(self, args: list[str], *, stream: bool = False, check: bool = True):
        cmd = [*self._base_cmd(), *args]
        return self.runner.run(cmd, stream=stream, check=check)

    def is_maintenance_on(self) -> bool:
        r = self.run(["maintenance:mode"], stream=False, check=False)
        text = (r.stdout or "") + (r.stderr or "")
        return "enabled: true" in text.lower() or "maintenance mode: enabled" in text.lower()

    def maintenance_on(self) -> None:
        console.print("[cyan]Maintenance mode: på[/cyan]")
        self.run(["maintenance:mode", "--on"], stream=True, check=True)

    def maintenance_off(self) -> None:
        console.print("[cyan]Maintenance mode: av[/cyan]")
        self.run(["maintenance:mode", "--off"], stream=True, check=True)

    @contextmanager
    def maintenance_session(self, *, enable: bool = True):
        """Slår på maintenance vid enter och av vid exit om vi slog på den."""
        was_on = self.is_maintenance_on()
        turned_on = False
        try:
            if enable and not was_on:
                self.maintenance_on()
                turned_on = True
            yield
        finally:
            if turned_on:
                try:
                    self.maintenance_off()
                except Exception:
                    console.print("[red]Varning: kunde inte stänga av maintenance mode.[/red]")

    def config_delete(self, key: str) -> None:
        self.run(["config:system:delete", key], stream=False, check=False)

    def config_set(self, key: str, value: str, *, type_: str | None = None) -> None:
        cmd = ["config:system:set", key, "--value", value]
        if type_:
            cmd.extend(["--type", type_])
        self.run(cmd, stream=False, check=True)

    def version_string(self) -> str | None:
        st = self.get_status()
        return st.versionstring

    def get_status(self) -> OccStatus:
        r = self.run(["status", "--output=json"], stream=False, check=False)
        if r.ok and r.stdout.strip():
            try:
                data = json.loads(r.stdout.strip())
                return OccStatus(
                    installed=data.get("installed"),
                    versionstring=data.get("versionstring") or data.get("version"),
                    maintenance=data.get("maintenance"),
                    raw=r.stdout,
                )
            except json.JSONDecodeError:
                pass
        r2 = self.run(["status"], stream=False, check=False)
        raw = (r2.stdout or "") + ("\n" + r2.stderr if r2.stderr else "")
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

    def run_upgrade(self) -> None:
        self.run(["upgrade"], stream=True, check=True)

    def run_with_maintenance_toggle(self, args: list[str]) -> None:
        """
        Motsvarar nextcloud_occ_no_check: om maintenance är på, stäng av, kör, slå på igen.
        """
        was_on = self.is_maintenance_on()
        if was_on:
            self.run(["maintenance:mode", "--off"], stream=False, check=True)
        try:
            self.run(args, stream=True, check=True)
        finally:
            if was_on:
                self.run(["maintenance:mode", "--on"], stream=False, check=True)


def get_status() -> OccStatus:
    from ..core.runner import ProcessRunner

    return NextcloudOcc(ProcessRunner(echo_commands=False)).get_status()
