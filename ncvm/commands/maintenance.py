from __future__ import annotations

from ..core.occ import occ


def maintenance_on() -> int:
    return occ(["maintenance:mode", "--on"]).returncode


def maintenance_off() -> int:
    return occ(["maintenance:mode", "--off"]).returncode

