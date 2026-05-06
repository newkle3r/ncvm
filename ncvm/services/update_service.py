from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner
from .apache import ApacheService
from .apt import AptService
from .nc_upgrade import NextcloudUpgradeService
from .occ import NextcloudOcc
from .php import PhpService
from .redis import RedisService
from .systemd import SystemdService


@dataclass
class UpdateResult:
    ok: bool
    message: str = ""


class UpdateService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        runner: ProcessRunner | None = None,
        debug: bool = False,
    ):
        self.settings = settings or get_settings()
        log_path = None
        if os.name != "nt":
            log_path = Path(self.settings.vm_log_dir) / "ncvm.log"
        self.runner = runner or ProcessRunner(
            use_sudo=True,
            log_path=log_path,
            tag="ncvm",
            debug=debug,
        )
        self.apt = AptService(self.runner, self.settings)
        self.systemd = SystemdService(self.runner, self.settings)
        self.apache = ApacheService(self.runner, self.settings)
        self.php = PhpService(self.runner, self.settings)
        self.occ = NextcloudOcc(self.runner, self.settings)
        self.redis = RedisService(self.runner, self.occ, self.settings)
        self.nc_upgrade = NextcloudUpgradeService(self.runner, self.occ, self.settings)

    def _ubuntu_release(self) -> float:
        if os.name == "nt":
            return 24.04
        r = self.runner.run(["lsb_release", "-sr"], stream=False, check=False)
        try:
            return float((r.stdout or "24.04").strip())
        except ValueError:
            return 24.04

    def update_php(self, phpver: str | None = None, *, dry_run: bool = False) -> UpdateResult:
        ver = (phpver or self.settings.default_phpver).strip()
        if dry_run:
            console.print(f"[yellow]DRY-RUN: skulle köra PHP-uppgradering till {ver}[/yellow]")
            return UpdateResult(True, "dry-run")

        self.apt.wait_for_lock()
        self.apt.install_if_missing("software-properties-common")
        self.apt.install_if_missing("ca-certificates")
        self.apt.update_ca_certificates()

        rel = self._ubuntu_release()
        if 16.04 <= rel <= 24.04:
            self.apt.add_ppa("ppa:ondrej/php")

        self.apt.unhold("php*")
        self.apt.update()

        self.occ.maintenance_on()
        try:
            self.systemd.stop(self.settings.apache_service)

            for key in (
                "memcache.local",
                "memcache.distributed",
                "filelocking.enabled",
                "memcache.locking",
                "redis",
            ):
                self.occ.config_delete(key)

            self.php.purge_all_php()
            self.apt.update()
            self.php.install_nextcloud_php_stack(ver)
            self.php.enable_apache_modules(ver)
            self.php.write_fpm_pool(ver)
            self.php.enable_php_modules(["igbinary", "redis", "opcache"])
            self.php.apply_opcache_ini(ver)
            self.php.restart_webserver_stack(ver)

            self.redis.install_server()
            self.redis.configure_for_nextcloud()
        finally:
            self.occ.maintenance_off()

        return UpdateResult(True, f"PHP {ver} installerad.")

    def update_nextcloud(
        self,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        skip_apps_backup: bool = False,
    ) -> UpdateResult:
        if dry_run:
            console.print("[yellow]DRY-RUN: skulle köra Nextcloud-uppgradering[/yellow]")
            return UpdateResult(True, "dry-run")

        self.apt.wait_for_lock()
        self.occ.maintenance_on()
        try:
            self.nc_upgrade.upgrade_to_latest(skip_backup=skip_backup, skip_apps_backup=skip_apps_backup)
        finally:
            self.occ.maintenance_off()

        return UpdateResult(True, "Nextcloud uppgraderad.")

    def update_all(
        self,
        *,
        phpver: str | None = None,
        dry_run: bool = False,
        skip_backup: bool = False,
        skip_apps_backup: bool = False,
    ) -> UpdateResult:
        r1 = self.update_nextcloud(dry_run=dry_run, skip_backup=skip_backup, skip_apps_backup=skip_apps_backup)
        if not r1.ok:
            return r1
        r2 = self.update_php(phpver=phpver, dry_run=dry_run)
        return r2
