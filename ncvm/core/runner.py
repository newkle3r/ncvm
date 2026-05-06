from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Sequence

from .console import console

log = logging.getLogger("ncvm")


class RunError(RuntimeError):
    def __init__(self, message: str, *, cmd: list[str], returncode: int):
        super().__init__(message)
        self.cmd = cmd
        self.returncode = returncode


@dataclass(frozen=True)
class RunResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _has_sudo() -> bool:
    try:
        p = subprocess.run(
            ["bash", "-lc", "command -v sudo >/dev/null 2>&1"],
            check=False,
            capture_output=True,
            text=True,
        )
        return p.returncode == 0
    except OSError:
        return False


def require_root_or_sudo() -> None:
    if os.name == "nt":
        return
    if os.geteuid() == 0:
        return
    if not _has_sudo():
        raise SystemExit("Måste köras som root eller ha sudo installerat/konfigurerat.")


def maybe_sudo(cmd: list[str], *, use_sudo: bool) -> list[str]:
    if not use_sudo or os.name == "nt":
        return cmd
    if os.geteuid() == 0:
        return cmd
    return ["sudo", *cmd]


def default_log_path() -> Path:
    return Path("/var/log/nextcloud/ncvm.log")


class ProcessRunner:
    """
    Kör subprocess med valfri live-stream till terminal + loggfil.
    """

    def __init__(
        self,
        *,
        use_sudo: bool = True,
        log_path: Path | None = None,
        tag: str = "ncvm",
        debug: bool = False,
        echo_commands: bool = True,
    ):
        self.use_sudo = use_sudo
        self.log_path = log_path
        self.tag = tag
        self.debug = debug
        self.echo_commands = echo_commands

    def _open_log(self) -> IO[str] | None:
        if self.log_path is None:
            p = default_log_path()
        else:
            p = self.log_path
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            return open(p, "a", encoding="utf-8", errors="replace")
        except OSError:
            return None

    def run(
        self,
        argv: Sequence[str],
        *,
        stream: bool = True,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> RunResult:
        cmd = list(argv)
        if self.debug:
            log.debug("run: %s", shlex.join(cmd))
        if self.echo_commands:
            console.print(f"[cyan]Kör:[/cyan] {shlex.join(cmd)}")

        if stream:
            return self._run_stream(cmd, check=check, env=env)
        return self._run_capture(cmd, check=check, env=env)

    def _run_capture(
        self,
        cmd: list[str],
        *,
        check: bool,
        env: dict[str, str] | None,
    ) -> RunResult:
        p = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            env={**os.environ, **(env or {})},
        )
        res = RunResult(cmd, p.returncode, p.stdout or "", p.stderr or "")
        if check and not res.ok:
            raise RunError(
                f"Kommando misslyckades (exit {res.returncode}): {shlex.join(cmd)}",
                cmd=cmd,
                returncode=res.returncode,
            )
        return res

    def _run_stream(
        self,
        cmd: list[str],
        *,
        check: bool,
        env: dict[str, str] | None,
    ) -> RunResult:
        log_fh = self._open_log()
        merged_env = {**os.environ, **(env or {})}

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=merged_env,
        )

        out_buf: list[str] = []
        err_buf: list[str] = []

        def pump(pipe: IO[str] | None, prefix: str, buf: list[str]) -> None:
            if pipe is None:
                return
            try:
                for line in iter(pipe.readline, ""):
                    if not line:
                        break
                    buf.append(line)
                    console.print(f"{prefix}{line}", end="")
                    if log_fh:
                        log_fh.write(f"[{self.tag}]{prefix}{line}")
                        log_fh.flush()
            finally:
                pipe.close()

        t_out = threading.Thread(target=pump, args=(proc.stdout, "", out_buf))
        t_err = threading.Thread(target=pump, args=(proc.stderr, "[stderr] ", err_buf))
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()
        rc = proc.wait()
        if log_fh:
            log_fh.close()

        res = RunResult(cmd, rc, "".join(out_buf), "".join(err_buf))
        if check and not res.ok:
            raise RunError(
                f"Kommando misslyckades (exit {res.returncode}): {shlex.join(cmd)}",
                cmd=cmd,
                returncode=res.returncode,
            )
        return res

    def sudo(self, args: list[str], **kwargs) -> RunResult:
        return self.run(maybe_sudo(args, use_sudo=self.use_sudo), **kwargs)
