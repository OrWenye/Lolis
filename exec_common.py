from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path


DEFAULT_SHELL_TIMEOUT_MS = 20_000
DEFAULT_TEST_TIMEOUT_MS = 120_000
MAX_TIMEOUT_MS = 300_000

ALLOWED_COMMANDS = {
    "node",
    "npm",
    "npx",
    "pip",
    "pip3",
    "pnpm",
    "py",
    "pytest",
    "python",
    "python3",
    "rg",
    "uv",
    "yarn",
}


def workspace_root() -> Path:
    return Path.cwd().resolve()


def normalize_timeout_ms(timeout_ms: int | None, default_ms: int) -> tuple[int, str | None]:
    if timeout_ms is None:
        return default_ms, None
    try:
        value = int(timeout_ms)
    except (TypeError, ValueError):
        return 0, "timeout_ms must be an integer"
    if value <= 0:
        return 0, "timeout_ms must be greater than 0"
    return min(value, MAX_TIMEOUT_MS), None


def resolve_workdir(workdir: str | None) -> tuple[Path, str | None]:
    root = workspace_root()
    if not workdir:
        return root, None

    candidate = Path(workdir)
    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        return root, f"workdir escapes workspace: {exc}"

    if not resolved.exists():
        return root, "workdir does not exist"
    if not resolved.is_dir():
        return root, "workdir is not a directory"
    return resolved, None


def command_name(command: str) -> str:
    name = Path(command).name.lower()
    if name.endswith((".exe", ".cmd", ".bat")):
        return Path(name).stem
    return name


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def split_command(command: str) -> tuple[list[str], str | None]:
    if not command or not command.strip():
        return [], "command is required"
    try:
        if os.name == "nt":
            parts = [_strip_outer_quotes(part) for part in shlex.split(command.strip(), posix=False)]
        else:
            parts = shlex.split(command.strip())
    except ValueError as exc:
        return [], f"invalid command: {exc}"
    if not parts:
        return [], "command is required"
    if command_name(parts[0]) not in ALLOWED_COMMANDS:
        return [], f"command not allowed: {parts[0]}"
    return parts, None


def run_command(parts: list[str], *, command: str, workdir: Path, timeout_ms: int) -> dict:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            parts,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_ms / 1000,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "command": command,
            "workdir": str(workdir),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    except OSError as exc:
        return {
            "success": False,
            "command": command,
            "workdir": str(workdir),
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }

    return {
        "success": completed.returncode == 0,
        "command": command,
        "workdir": str(workdir),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
