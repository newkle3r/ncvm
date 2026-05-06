from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from urllib.request import urlopen

from ..config import Settings, get_settings
from ..core.console import console
from ..core.runner import ProcessRunner
from .occ import NextcloudOcc


class NextcloudUpgradeService:
    def __init__(self, runner: ProcessRunner, occ: NextcloudOcc, settings: Settings | None = None):
        self.runner = runner
        self.occ = occ
        self.settings = settings or get_settings()

    def fetch_latest_version(self) -> str:
        """Hämta senaste stabila versionsnummer från download.nextcloud.com (motsvarar nc_update)."""
        url = f"{self.settings.nc_download_base.rstrip('/')}/"
        with urlopen(url, timeout=900) as resp:  # noqa: S310
            html = resp.read().decode("utf-8", errors="replace")
        versions = re.findall(r'href="nextcloud-([^"]+)\.zip\.asc"', html)
        if not versions:
            raise RuntimeError("Kunde inte tolka versionslista från Nextcloud releases.")
        def ver_key(v: str) -> tuple[int, ...]:
            out: list[int] = []
            for p in v.split("."):
                try:
                    out.append(int(p))
                except ValueError:
                    out.append(0)
            return tuple(out)

        versions_sorted = sorted(set(versions), key=ver_key)
        return versions_sorted[-1]

    def write_major_hint(self, current_version: str) -> None:
        major = int(current_version.split(".", 1)[0])
        hint = str(major - 2)
        fd, tmp = tempfile.mkstemp(prefix="nextmajor-", dir="/tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(hint + "\n")
            self.runner.sudo(["cp", tmp, "/tmp/nextmajor.version"], stream=False, check=True)
        finally:
            try:
                Path(tmp).unlink()
            except OSError:
                pass

    def backup_nextcloud_dirs(self, *, skip_apps: bool = False) -> None:
        backup = Path(self.settings.backup_dir)
        nc = Path(self.settings.nextcloud_dir)
        self.runner.sudo(["mkdir", "-p", str(backup)], stream=True, check=True)
        subs: tuple[str, ...] = ("config",) if skip_apps else ("config", "apps")
        for sub in subs:
            src = nc / sub
            if self.runner.sudo(["test", "-d", str(src)], stream=False, check=False).returncode == 0:
                console.print(f"[cyan]Backup: rsync {src} -> {backup}[/cyan]")
                # Helps operators understand why rsync may look "stuck".
                self.runner.sudo(["du", "-sh", str(src)], stream=True, check=False)
                self.runner.sudo(
                    [
                        "rsync",
                        "-Aax",
                        "--human-readable",
                        "--info=progress2",
                        str(src) + "/",
                        str(backup / sub) + "/",
                    ],
                    stream=True,
                    check=True,
                )

    def upgrade_to_latest(self, *, skip_backup: bool = False, skip_apps_backup: bool = False) -> None:
        current = self.occ.version_string()
        if not current:
            raise RuntimeError("Kunde inte läsa nuvarande Nextcloud-version (occ).")
        latest = self.fetch_latest_version()
        console.print(f"[cyan]Nuvarande: {current}  Senaste release: {latest}[/cyan]")
        self.write_major_hint(current)

        if not skip_backup:
            self.backup_nextcloud_dirs(skip_apps=skip_apps_backup)

        stable = f"nextcloud-{latest}"
        base = self.settings.nc_download_base.rstrip("/")
        work = Path("/tmp/ncvm-nc-upgrade")
        self.runner.sudo(["rm", "-rf", str(work)], stream=False, check=False)
        self.runner.sudo(["mkdir", "-p", str(work)], stream=True, check=True)

        tar_url = f"{base}/{stable}.tar.bz2"
        sha_url = f"{base}/{stable}.tar.bz2.sha256"
        asc_url = f"{base}/{stable}.tar.bz2.asc"
        tar_path = work / f"{stable}.tar.bz2"
        sha_path = work / f"{stable}.tar.bz2.sha256"
        asc_path = work / f"{stable}.tar.bz2.asc"

        self.runner.sudo(
            ["curl", "-fSL", "--retry", "3", tar_url, "-o", str(tar_path)],
            stream=True,
            check=True,
        )
        self.runner.sudo(["curl", "-fSL", sha_url, "-o", str(sha_path)], stream=True, check=True)
        self.runner.sudo(["curl", "-fSL", asc_url, "-o", str(asc_path)], stream=True, check=True)

        self.runner.sudo(
            [
                "bash",
                "-lc",
                (
                    f"cd {work} && "
                    f"line=$(grep -E '(^| )({tar_path.name})$' {sha_path.name} | tail -n 1) && "
                    f"test -n \"$line\" && "
                    f"echo \"$line\" | sha256sum -c"
                ),
            ],
            stream=True,
            check=True,
        )

        fp = self.settings.nextcloud_gpg_fingerprint
        self.runner.sudo(["apt-get", "install", "-y", "gnupg"], stream=True, check=False)
        self.runner.sudo(
            ["bash", "-lc", f"gpg --keyserver hkps://keys.openpgp.org --recv-keys {fp} || gpg --keyserver hkp://keyserver.ubuntu.com --recv-keys {fp}"],
            stream=True,
            check=True,
        )
        self.runner.sudo(
            ["gpg", "--verify", str(asc_path), str(tar_path)],
            stream=True,
            check=True,
        )

        extract_root = work / "extract"
        self.runner.sudo(["mkdir", "-p", str(extract_root)], stream=True, check=True)
        self.runner.sudo(["tar", "-xjf", str(tar_path), "-C", str(extract_root)], stream=True, check=True)

        src_nc = extract_root / stable
        if self.runner.sudo(["test", "-d", str(src_nc)], stream=False, check=False).returncode != 0:
            # vissa arkiv har top-level "nextcloud"
            alt = extract_root / "nextcloud"
            if self.runner.sudo(["test", "-d", str(alt)], stream=False, check=False).returncode == 0:
                src_nc = alt
            else:
                raise RuntimeError(f"Hittade inte extraherad katalog för {stable}")

        dest = Path(self.settings.nextcloud_dir)
        console.print(f"[cyan]Synkar {src_nc} -> {dest} (exkluderar data/ och config.php)[/cyan]")
        self.runner.sudo(
            [
                "rsync",
                "-Aax",
                "--delete",
                "--exclude=data/",
                "--exclude=config/config.php",
                f"{src_nc}/",
                f"{dest}/",
            ],
            stream=True,
            check=True,
        )
        self.runner.sudo(["chown", "-R", f"{self.settings.www_user}:{self.settings.www_user}", str(dest)], stream=True, check=True)

        self.occ.run_upgrade()

        self.runner.sudo(["rm", "-rf", str(work)], stream=True, check=False)
