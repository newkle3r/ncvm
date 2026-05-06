from __future__ import annotations

from ..config import Settings, get_settings
from ..core.runner import ProcessRunner


class SystemdService:
    def __init__(self, runner: ProcessRunner, settings: Settings | None = None):
        self.runner = runner
        self.settings = settings or get_settings()

    def is_active(self, unit: str) -> bool:
        try:
            r = self.runner.sudo(
                ["systemctl", "is-active", "--quiet", unit],
                stream=False,
                check=False,
            )
            return r.returncode == 0
        except Exception:
            return False

    def start(self, unit: str) -> None:
        self.runner.sudo(["systemctl", "start", unit], stream=True, check=True)

    def stop(self, unit: str) -> None:
        self.runner.sudo(["systemctl", "stop", unit], stream=True, check=True)

    def restart(self, unit: str) -> None:
        self.runner.sudo(["systemctl", "restart", unit], stream=True, check=True)

    def enable(self, unit: str) -> None:
        self.runner.sudo(["systemctl", "enable", "--now", unit], stream=True, check=False)
