from __future__ import annotations

from ..core.runner import ProcessRunner
from ..services.systemd import SystemdService


def is_active(service: str) -> bool:
    return SystemdService(ProcessRunner()).is_active(service)
