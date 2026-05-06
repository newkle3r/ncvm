from __future__ import annotations

"""
Bakåtkompatibelt lager: använd `ncvm.services.occ` för ny kod.
"""

from .runner import ProcessRunner, RunResult
from ..services.occ import NextcloudOcc, OccStatus


def occ(args: list[str]) -> RunResult:
    return NextcloudOcc(ProcessRunner(echo_commands=False)).run(args, stream=False, check=False)


def get_status() -> OccStatus:
    return NextcloudOcc(ProcessRunner(echo_commands=False)).get_status()


__all__ = ["OccStatus", "occ", "get_status", "RunResult"]
