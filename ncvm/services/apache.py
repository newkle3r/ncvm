from __future__ import annotations

from ..config import Settings, get_settings
from ..core.runner import ProcessRunner
from .systemd import SystemdService


class ApacheService:
    def __init__(self, runner: ProcessRunner, settings: Settings | None = None):
        self.runner = runner
        self.settings = settings or get_settings()
        self.systemd = SystemdService(runner, self.settings)

    def a2enmod(self, mods: list[str]) -> None:
        for m in mods:
            self.runner.sudo(["a2enmod", m], stream=True, check=False)

    def a2dismod(self, mods: list[str]) -> None:
        for m in mods:
            self.runner.sudo(["a2dismod", m], stream=True, check=False)

    def a2enconf(self, confs: list[str]) -> None:
        for c in confs:
            self.runner.sudo(["a2enconf", c], stream=True, check=False)

    def restart(self) -> None:
        self.systemd.restart(self.settings.apache_service)
