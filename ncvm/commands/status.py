from __future__ import annotations

from dataclasses import asdict

from ..core.occ import OccStatus, get_status
from ..core.runner import ProcessRunner
from ..services.systemd import SystemdService


def get_full_status() -> dict:
    st_occ: OccStatus = get_status()
    runner = ProcessRunner(echo_commands=False)
    systemd = SystemdService(runner)

    services = {
        "apache2": systemd.is_active("apache2"),
        "redis-server": systemd.is_active("redis-server"),
    }
    php_fpm_candidates = ["php8.3-fpm", "php8.2-fpm", "php8.1-fpm", "php-fpm"]
    php_fpm = None
    for svc in php_fpm_candidates:
        try:
            if systemd.is_active(svc):
                php_fpm = svc
                break
        except Exception:
            continue
    services["php-fpm"] = bool(php_fpm)
    services["php-fpm-service"] = php_fpm

    return {
        "nextcloud": asdict(st_occ),
        "services": services,
    }
