from __future__ import annotations

from ..core.runner import ProcessRunner
from ..services.php import PhpService


def optimize_php_fpm() -> None:
    PhpService(ProcessRunner()).calculate_php_fpm()
