from __future__ import annotations

from dataclasses import asdict

from ..core.occ import OccStatus, get_status
from ..core.systemd import is_active


def get_full_status() -> dict:
    occ_status: OccStatus = get_status()
    services = {
        "apache2": is_active("apache2"),
        "redis-server": is_active("redis-server"),
    }
    # php-fpm tjänstnamn varierar; prova de vanligaste
    php_fpm_candidates = ["php8.3-fpm", "php8.2-fpm", "php8.1-fpm", "php-fpm"]
    php_fpm = None
    for svc in php_fpm_candidates:
        try:
            if is_active(svc):
                php_fpm = svc
                break
        except Exception:
            continue
    services["php-fpm"] = bool(php_fpm)
    services["php-fpm-service"] = php_fpm

    return {
        "nextcloud": asdict(occ_status),
        "services": services,
    }

