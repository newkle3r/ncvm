from __future__ import annotations

from ..core.runner import ProcessRunner
from ..services.php import PhpService


def restart_webserver() -> None:
    PhpService(ProcessRunner()).restart_webserver_stack()
