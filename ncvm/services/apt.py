from __future__ import annotations

import shlex
import time

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner


class AptService:
    def __init__(self, runner: ProcessRunner, settings: Settings | None = None):
        self.runner = runner
        self.settings = settings or get_settings()

    def wait_for_lock(self, *, max_wait_s: int = 3600, interval_s: int = 30) -> None:
        """Vänta tills apt/dpkg inte kör (motsvarar is_process_running)."""
        waited = 0
        while waited < max_wait_s:
            r_apt = self.runner.sudo(
                ["bash", "-lc", "pgrep -x apt >/dev/null 2>&1 || pgrep -x apt-get >/dev/null 2>&1"],
                stream=False,
                check=False,
            )
            r_dpkg = self.runner.sudo(
                ["bash", "-lc", "pgrep -x dpkg >/dev/null 2>&1"],
                stream=False,
                check=False,
            )
            if r_apt.returncode != 0 and r_dpkg.returncode != 0:
                return
            console.print(f"[yellow]Väntar på apt/dpkg... ({waited}s)[/yellow]")
            time.sleep(interval_s)
            waited += interval_s
        raise TimeoutError("Timeout: apt/dpkg kör fortfarande efter max väntetid.")

    def update(self) -> None:
        self.runner.sudo(["apt-get", "update", "-q"], stream=True, check=True)

    def install(self, packages: list[str], *, extra_args: list[str] | None = None) -> None:
        args = ["apt-get", "install", "-y", *(extra_args or []), *packages]
        self.runner.sudo(args, stream=True, check=True)

    def install_if_missing(self, package: str) -> None:
        if self.is_installed(package):
            return
        self.install([package])

    def purge(self, patterns: list[str]) -> None:
        # patterns like "php*" -> pass to apt-get purge
        self.runner.sudo(["apt-get", "purge", "-y", *patterns], stream=True, check=True)

    def autoremove(self) -> None:
        self.runner.sudo(["apt-get", "autoremove", "-y"], stream=True, check=True)

    def autoclean(self) -> None:
        self.runner.sudo(["apt-get", "autoclean", "-y"], stream=True, check=False)

    def unhold(self, pattern: str) -> None:
        self.runner.sudo(["apt-mark", "unhold", pattern], stream=False, check=False)

    def is_installed(self, package: str) -> bool:
        q = shlex.quote(package)
        r = self.runner.sudo(
            [
                "bash",
                "-lc",
                f"dpkg-query -W -f='${{Status}}' {q} 2>/dev/null | grep -q 'ok installed'",
            ],
            stream=False,
            check=False,
        )
        return r.returncode == 0

    def add_ppa(self, ppa: str) -> None:
        self.install_if_missing("software-properties-common")
        self.runner.sudo(["add-apt-repository", "-y", ppa], stream=True, check=True)

    def update_ca_certificates(self) -> None:
        self.runner.sudo(["update-ca-certificates"], stream=True, check=False)
