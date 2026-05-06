from __future__ import annotations

import os
import re
import socket
import tempfile
from pathlib import Path

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner
from .apache import ApacheService
from .systemd import SystemdService


class PhpService:
    def __init__(self, runner: ProcessRunner, settings: Settings | None = None):
        self.runner = runner
        self.settings = settings or get_settings()
        self.systemd = SystemdService(runner, self.settings)
        self.apache = ApacheService(runner, self.settings)

    def detect_version(self) -> str:
        """Returnerar t.ex. '8.3' från `php -v` (motsvarar check_php)."""
        if os.name == "nt":
            return self.settings.default_phpver
        r = self.runner.run(["php", "-v"], stream=False, check=False)
        m = re.search(r"PHP\s+(\d+\.\d+)", (r.stdout or "") + (r.stderr or ""))
        return m.group(1) if m else self.settings.default_phpver

    def fpm_pool_path(self, phpver: str) -> Path:
        return Path(f"/etc/php/{phpver}/fpm/pool.d/nextcloud.conf")

    def php_ini_path(self, phpver: str) -> Path:
        return Path(f"/etc/php/{phpver}/fpm/php.ini")

    def purge_all_php(self) -> None:
        self.runner.sudo(["bash", "-lc", "DEBIAN_FRONTEND=noninteractive apt-get purge -y php* || true"], stream=True, check=False)
        self.runner.sudo(["apt-get", "autoremove", "-y"], stream=True, check=True)
        self.runner.sudo(["rm", "-rf", "/etc/php"], stream=True, check=False)

    def install_nextcloud_php_stack(self, phpver: str) -> None:
        pkgs = [
            f"php{phpver}-fpm",
            f"php{phpver}-intl",
            f"php{phpver}-ldap",
            f"php{phpver}-imap",
            f"php{phpver}-gd",
            f"php{phpver}-pgsql",
            f"php{phpver}-curl",
            f"php{phpver}-xml",
            f"php{phpver}-zip",
            f"php{phpver}-mbstring",
            f"php{phpver}-soap",
            f"php{phpver}-gmp",
            f"php{phpver}-bz2",
            f"php{phpver}-bcmath",
            f"php{phpver}-igbinary",
            f"php{phpver}-redis",
            f"php{phpver}-smbclient",
            "php-pear",
            "apache2",
        ]
        self.runner.sudo(["apt-get", "install", "-y", *pkgs], stream=True, check=True)

    def enable_apache_modules(self, phpver: str) -> None:
        mods = [
            "rewrite",
            "headers",
            "proxy",
            "proxy_fcgi",
            "setenvif",
            "env",
            "mime",
            "dir",
            "authz_core",
            "alias",
            "mpm_event",
            "ssl",
            "http2",
        ]
        self.apache.a2enmod(mods)
        self.apache.a2dismod(["mpm_prefork"])
        self.apache.a2enconf([f"php{phpver}-fpm"])

    def write_fpm_pool(self, phpver: str) -> None:
        pool = self.fpm_pool_path(phpver)
        self.runner.sudo(["mkdir", "-p", str(pool.parent)], stream=False, check=True)
        hostname = socket.getfqdn()
        content = f"""[Nextcloud]
user = www-data
group = www-data
listen = /run/php/php{phpver}-fpm.nextcloud.sock
listen.owner = www-data
listen.group = www-data
pm = dynamic
pm.max_children = 8
pm.start_servers = 3
pm.min_spare_servers = 2
pm.max_spare_servers = 3
env[HOSTNAME] = {hostname}
env[PATH] = /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
env[TMP] = /tmp
env[TMPDIR] = /tmp
env[TEMP] = /tmp
security.limit_extensions = .php
php_admin_value[cgi.fix_pathinfo] = 1
"""
        self._atomic_write(pool, content, mode=0o640)
        www_conf = pool.parent / "www.conf"
        self.runner.sudo(
            ["bash", "-lc", f"test -f {repr(str(www_conf))} && mv {repr(str(www_conf))} {repr(str(www_conf))}.backup || true"],
            stream=False,
            check=False,
        )

    def _chmod_octal(self, path: Path, mode: int) -> None:
        mode_s = format(mode & 0o777, "o")
        self.runner.sudo(["chmod", mode_s, str(path)], stream=False, check=True)

    def _atomic_write(self, path: Path, content: str, *, mode: int) -> None:
        fd, tmp = tempfile.mkstemp(prefix="ncvm-", suffix=path.suffix, dir="/tmp")
        try:
            os.chmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            self.runner.sudo(["cp", tmp, str(path)], stream=True, check=True)
            self.runner.sudo(["chown", "root:root", str(path)], stream=False, check=True)
            self._chmod_octal(path, mode)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def enable_php_modules(self, modules: list[str]) -> None:
        for mod in modules:
            self.runner.sudo(["phpenmod", "-v", "ALL", mod], stream=True, check=False)

    def apply_opcache_ini(self, phpver: str) -> None:
        ini = self.php_ini_path(phpver)
        marker = "; OPcache for Nextcloud (ncvm)"
        if ini.exists():
            r = self.runner.sudo(["cat", str(ini)], stream=False, check=False)
            if marker in (r.stdout or ""):
                return
        block = f"""
{marker}
opcache.enable=1
opcache.enable_cli=1
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.memory_consumption=256
opcache.save_comments=1
opcache.revalidate_freq=1
"""
        if self.runner.sudo(["test", "-f", str(ini)], stream=False, check=False).returncode == 0:
            cur = self.runner.sudo(["cat", str(ini)], stream=False, check=True).stdout or ""
            self._atomic_write(ini, cur + block, mode=0o644)
        else:
            self.runner.sudo(["mkdir", "-p", str(ini.parent)], stream=False, check=True)
            self._atomic_write(ini, block.lstrip("\n"), mode=0o644)

    def restart_fpm(self, phpver: str) -> None:
        self.systemd.restart(f"php{phpver}-fpm")

    def restart_webserver_stack(self, phpver: str | None = None) -> None:
        """motsvarar restart_webserver i lib.sh"""
        self.runner.run(["bash", "-lc", "sleep 2"], stream=False, check=False)
        console.print("[cyan]Startar om Apache2 och PHP-FPM...[/cyan]")
        self.apache.restart()
        ver = phpver or self.detect_version()
        if self._fpm_installed(ver):
            self.restart_fpm(ver)

    def _fpm_installed(self, phpver: str) -> bool:
        r = self.runner.sudo(
            ["bash", "-lc", f"dpkg-query -W -f='${{Status}}' php{phpver}-fpm 2>/dev/null | grep -q ok"],
            stream=False,
            check=False,
        )
        return r.returncode == 0

    def _read_remote_file(self, path: Path) -> str:
        r = self.runner.sudo(["cat", str(path)], stream=False, check=True)
        return r.stdout or ""

    def calculate_php_fpm(self, phpver: str | None = None) -> None:
        """Port av calculate_php_fpm (pm.max_children m.m.)."""
        ver = phpver or self.detect_version()
        pool = self.fpm_pool_path(ver)
        if self.runner.sudo(["test", "-f", str(pool)], stream=False, check=False).returncode != 0:
            raise FileNotFoundError(f"Saknar pool-fil: {pool}")

        min_max_children = 8
        min_start_servers = 20
        min_max_spare_servers = 35
        average_mb = 50

        mem_kb = 0
        p = Path("/proc/meminfo")
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("MemAvailable:"):
                    mem_kb = int(line.split()[1])
                    break
        available_mb = mem_kb // 1024 if mem_kb else 0
        php_fpm_max = max(min_max_children, available_mb // average_mb) if available_mb else min_max_children

        txt = self._read_remote_file(pool)

        def grab(pat: str) -> int:
            m = re.search(pat, txt, flags=re.MULTILINE)
            if not m:
                return 0
            return int(m.group(1))

        current_start = grab(r"^pm\.start_servers\s*=\s*(\d+)")
        current_max_spare = grab(r"^pm\.max_spare_servers\s*=\s*(\d+)")
        current_min_spare = grab(r"^pm\.min_spare_servers\s*=\s*(\d+)")
        current_sum = current_start + current_max_spare + current_min_spare

        def sub(key: str, val: int) -> None:
            nonlocal txt
            txt = re.sub(rf"^{re.escape(key)}\s*=.*$", f"{key} = {val}", txt, flags=re.MULTILINE)

        sub("pm.max_children", php_fpm_max)
        console.print(f"[green]pm.max_children satt till {php_fpm_max}[/green]")

        if php_fpm_max > current_sum and php_fpm_max >= min_max_spare_servers:
            start_val = grab(r"^pm\.start_servers\s*=\s*(\d+)")
            if start_val < min_start_servers:
                new_spare = max(1, php_fpm_max - 30)
                sub("pm.max_spare_servers", new_spare)
                console.print(f"[green]pm.max_spare_servers satt till {new_spare}[/green]")

        if php_fpm_max < current_sum:
            sub("pm.max_children", php_fpm_max)
            sub("pm.start_servers", 3)
            sub("pm.min_spare_servers", 2)
            sub("pm.max_spare_servers", 3)
            console.print(
                "[yellow]pm-värden återställda till default pga lågt max vs summa; kör optimize igen.[/yellow]"
            )

        self._atomic_write(pool, txt, mode=0o640)
        self.restart_webserver_stack(ver)
