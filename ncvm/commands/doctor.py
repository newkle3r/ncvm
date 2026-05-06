from __future__ import annotations

import json
from pathlib import Path

from ..config import get_settings
from ..core.occ import get_status
from ..core.runner import ProcessRunner, require_root_or_sudo
from ..services.systemd import SystemdService


def run_doctor(*, as_json: bool = False) -> str:
    st = get_settings()
    require_root_or_sudo()

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
