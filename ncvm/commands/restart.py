from __future__ import annotations

from ..core.bash import CmdResult, source_lib_and_call


def restart_webserver() -> CmdResult:
    return source_lib_and_call("restart_webserver")

