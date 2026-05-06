from __future__ import annotations

import os
import re
import secrets
import string
import tempfile
from pathlib import Path

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner
from .occ import NextcloudOcc
from .systemd import SystemdService


class RedisService:
    def __init__(self, runner: ProcessRunner, occ: NextcloudOcc, settings: Settings | None = None):
        self.runner = runner
        self.occ = occ
        self.settings = settings or get_settings()
        self.systemd = SystemdService(runner, self.settings)

    @staticmethod
    def generate_password(length: int = 24) -> str:
        alphabet = string.ascii_letters + string.digits + "@#*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def install_server(self) -> None:
        self.runner.sudo(["apt-get", "install", "-y", "redis-server"], stream=True, check=True)
        self.systemd.enable("redis-server")

    def configure_for_nextcloud(self, *, password: str | None = None) -> str:
        """
        Konfigurerar redis-server (socket, port 0) och Nextcloud occ (redis + memcache).
        Returnerar redis-lösenordet som satts.
        """
        pw = password or self.generate_password()
        conf = Path(self.settings.redis_conf)
        sock = self.settings.redis_sock

        raw = self.runner.sudo(["cat", str(conf)], stream=False, check=True).stdout or ""

        def set_line(content: str, key: str, value: str) -> str:
            pat = rf"^[# ]*{re.escape(key)}\b.*$"
            repl = f"{key} {value}"
            if re.search(pat, content, flags=re.MULTILINE):
                return re.sub(pat, repl, content, flags=re.MULTILINE)
            return content.rstrip() + "\n" + repl + "\n"

        out = raw
        out = set_line(out, "unixsocket", sock)
        out = set_line(out, "unixsocketperm", "777")
        out = set_line(out, "port", "0")
        out = re.sub(
            r"^[# ]*requirepass\b.*$",
            f"requirepass {pw}",
            out,
            flags=re.MULTILINE,
        )
        if "requirepass" not in out or not re.search(rf"^requirepass\s+{re.escape(pw)}\s*$", out, re.MULTILINE):
            out = out.rstrip() + f"\nrequirepass {pw}\n"

        fd, tmp = tempfile.mkstemp(prefix="ncvm-redis-", suffix=".conf", dir="/tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                f.write(out)
            self.runner.sudo(["cp", tmp, str(conf)], stream=True, check=True)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

        self.runner.sudo(["sysctl", "-w", "vm.overcommit_memory=1"], stream=False, check=False)
        self.runner.sudo(
            ["bash", "-lc", "grep -q 'vm.overcommit_memory' /etc/sysctl.conf || echo 'vm.overcommit_memory = 1' | tee -a /etc/sysctl.conf"],
            stream=False,
            check=False,
        )
        self.systemd.restart("redis-server")

        # Nextcloud
        self.occ.run(["config:system:set", "redis", "host", "--value", sock], stream=False, check=True)
        self.occ.run(["config:system:set", "redis", "port", "--value", "0", "--type", "integer"], stream=False, check=True)
        self.occ.run(["config:system:set", "redis", "dbindex", "--value", "0", "--type", "integer"], stream=False, check=True)
        self.occ.run(["config:system:set", "redis", "timeout", "--value", "0.5", "--type", "float"], stream=False, check=True)
        self.occ.run(["config:system:set", "redis", "password", "--value", pw], stream=False, check=True)
        self.occ.run(
            ["config:system:set", "memcache.local", "--value", "\\OC\\Memcache\\Redis"],
            stream=False,
            check=True,
        )
        self.occ.run(["config:system:set", "filelocking.enabled", "--value", "true", "--type", "boolean"], stream=False, check=True)
        self.occ.run(
            ["config:system:set", "memcache.distributed", "--value", "\\OC\\Memcache\\Redis"],
            stream=False,
            check=True,
        )
        self.occ.run(
            ["config:system:set", "memcache.locking", "--value", "\\OC\\Memcache\\Redis"],
            stream=False,
            check=True,
        )

        self.systemd.restart("redis-server")
        self.runner.sudo(["chown", "redis:root", str(conf)], stream=False, check=False)
        self.runner.sudo(["chmod", "600", str(conf)], stream=False, check=False)

        console.print(f"[green]Redis konfigurerad. Lösenord (spara säkert): {pw}[/green]")
        return pw
