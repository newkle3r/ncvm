from __future__ import annotations

import json
import os
from pathlib import Path

from ..config import get_settings
from ..core.occ import get_status
from ..core.runner import ProcessRunner, require_root_or_sudo
from ..services.systemd import SystemdService


def run_doctor(*, as_json: bool = False) -> str:
    st = get_settings()
    require_root_or_sudo()

    # On Windows, many checks rely on bash/sudo/Unix paths and can hang depending on the environment.
    # Return a minimal report instead of attempting Linux-only checks.
    if os.name == "nt":
        minimal: dict[str, object] = {
            "platform": "windows",
            "note": "Doctor-checkar är primärt för Linux/Nextcloud VM. Kör på servern för full rapport.",
            "paths": {
                "scripts_dir_exists": Path(st.scripts_dir).exists(),
                "nextcloud_dir_exists": Path(st.nextcloud_dir).exists(),
                "occ_path_exists": Path(st.occ_path).exists(),
            },
            "nextcloud": {
                "installed": None,
                "versionstring": None,
                "maintenance": None,
            },
        }
        return json.dumps(minimal, ensure_ascii=False, indent=2) if as_json else "\n".join(
            [
                "Doctor-rapport",
                "",
                "Obs: Doctor-checkar är primärt för Linux/Nextcloud VM. Kör på servern för full rapport.",
            ]
        )

    runner = ProcessRunner(echo_commands=False)
    systemd = SystemdService(runner, st)

    checks: dict[str, object] = {}
    checks["paths"] = {
        "scripts_dir_exists": Path(st.scripts_dir).exists(),
        "nextcloud_dir_exists": Path(st.nextcloud_dir).exists(),
        "occ_path_exists": Path(st.occ_path).exists(),
    }

    checks["services"] = {
        "apache2_active": systemd.is_active("apache2"),
        "redis-server_active": systemd.is_active("redis-server"),
    }

    bins = ["bash", "curl", "php", "systemctl"]
    checks["binaries"] = {
        b: runner.run(["bash", "-lc", f"command -v {b} >/dev/null 2>&1"], stream=False, check=False).ok
        for b in bins
    }

    # Common Nextcloud VM issues
    nc_dir = Path(st.nextcloud_dir)
    data_dir = nc_dir / "data"
    ocdata = data_dir / ".ocdata"
    redis_sock = Path(st.redis_sock)

    def _ok(cmd: str) -> bool:
        return runner.run(["bash", "-lc", cmd], stream=False, check=False).ok

    def _stdout(cmd: str) -> str:
        r = runner.run(["bash", "-lc", cmd], stream=False, check=False)
        return (r.stdout or "").strip()

    checks["permissions"] = {
        "nextcloud_owned_by_www_user": _ok(f"test \"$(stat -c %U {nc_dir})\" = \"{st.www_user}\""),
        "config_writable_by_www_user": _ok(f"sudo -u {st.www_user} test -w {nc_dir}/config"),
        "apps_writable_by_www_user": _ok(f"sudo -u {st.www_user} test -w {nc_dir}/apps"),
        "data_writable_by_www_user": _ok(f"sudo -u {st.www_user} test -w {data_dir}"),
    }

    checks["nextcloud_data"] = {
        "data_dir_exists": data_dir.exists(),
        "ocdata_exists": ocdata.exists(),
        "ocdata_path": str(ocdata),
    }

    checks["redis"] = {
        "redis_sock_path": str(redis_sock),
        "redis_sock_exists": redis_sock.exists(),
        "redis_sock_readable_by_www_user": _ok(f"sudo -u {st.www_user} test -r {redis_sock}"),
        "redis_ping_via_socket": _ok(
            f"command -v redis-cli >/dev/null 2>&1 && redis-cli -s {redis_sock} ping >/dev/null 2>&1"
        ),
    }

    checks["system"] = {
        "backup_dir_mount": _stdout(f"mount | grep -F \" {st.backup_dir} \" || true"),
        "backup_dir_df": _stdout(f"df -h {st.backup_dir} 2>/dev/null | tail -n 1 || true"),
    }

    occ_status = get_status()
    checks["nextcloud"] = {
        "installed": occ_status.installed,
        "versionstring": occ_status.versionstring,
        "maintenance": occ_status.maintenance,
    }

    if as_json:
        return json.dumps(checks, ensure_ascii=False, indent=2)

    lines: list[str] = []
    lines.append("Doctor-rapport")
    lines.append("")
    lines.append("Paths:")
    for k, v in (checks["paths"] or {}).items():  # type: ignore[union-attr]
        lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("Services:")
    for k, v in (checks["services"] or {}).items():  # type: ignore[union-attr]
        lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("Binaries:")
    for k, v in (checks["binaries"] or {}).items():  # type: ignore[union-attr]
        lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("Nextcloud:")
    for k, v in (checks["nextcloud"] or {}).items():  # type: ignore[union-attr]
        lines.append(f"  - {k}: {v}")
    return "\n".join(lines)
