from __future__ import annotations

from ..core.bash import CmdResult, source_lib_and_call


def optimize_php_fpm() -> CmdResult:
    # använder samma logik som VM: calculate_php_fpm -> restart_webserver
    return source_lib_and_call("calculate_php_fpm")

