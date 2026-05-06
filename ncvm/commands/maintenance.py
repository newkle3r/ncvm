from __future__ import annotations

from ..core.runner import ProcessRunner, RunError
from ..services.occ import NextcloudOcc


def maintenance_on() -> int:
    try:
        NextcloudOcc(ProcessRunner()).maintenance_on()
        return 0
    except RunError:
        return 1


def maintenance_off() -> int:
    try:
        NextcloudOcc(ProcessRunner()).maintenance_off()
        return 0
    except RunError:
        return 1
