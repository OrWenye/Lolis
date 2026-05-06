from __future__ import annotations

import subprocess
import time
from pathlib import Path


DEFAULT_TIMEOUT_MS = 120_000
MAX_TIMEOUT_MS = 300_000

# 只允许固定测试命令入口，避免这个工具退化成任意命令执行器。
TEST_RUNNERS = {
    "pytest": ["pytest"],
    "python_pytest": ["python", "-m", "pytest"],
    "uv_pytest": ["uv", "run", "pytest"],
    "npm": ["npm", "test", "--"],
}


def run_test_command(
    runner: str = "pytest",
    target: str | None = None,
    extra_args: list[str] | None = None,
    workdir: str | None = None,
    timeout_ms: int | None = None,
) -> dict:
    """
    执行测试命令并返回结构化结果。

    参数：
    - runner (str): 测试运行器类型，默认 "pytest"。支持 "pytest", "python_pytest", "uv_pytest", "npm"。
    - target (str | None): 测试目标路径，默认 None。
    - extra_args (list[str] | None): 额外命令行参数列表，默认 None。
    - workdir (str | None): 执行命令的工作目录，默认当前目录。
    - timeout_ms (int | None): 超时时间（毫秒），默认 120000。

    返回：dict - 执行结果字典，包含 success, runner, command, workdir, exit_code, stdout, stderr, timed_out, duration_ms 等字段。

    适用场景：
    - QA Worker 跑单元测试
    - Delivery Worker 在修复后做快速回归
    - Supervisor 收集测试结果决定是否继续
    """
    # runner 决定测试命令前缀，例如 pytest / python -m pytest / npm test。
    command_prefix = TEST_RUNNERS.get(runner)
    if command_prefix is None:
        return {
            "success": False,
            "error": f"unsupported runner: {runner}",
            "code": "invalid_runner",
        }

    # workdir 被限制在当前工作区内，避免工具跑到项目外部。
    resolved_workdir, error = _resolve_workdir(workdir)
    if error:
        return {
            "success": False,
            "error": error,
            "code": "invalid_workdir",
        }

    # timeout 统一转成毫秒整数，并做上限保护。
    resolved_timeout, error = _normalize_timeout_ms(timeout_ms)
    if error:
        return {
            "success": False,
            "error": error,
            "code": "invalid_timeout",
        }

    if extra_args is not None and not isinstance(extra_args, list):
        return {
            "success": False,
            "error": "extra_args must be a list of strings",
            "code": "invalid_args",
        }

    # 最终命令由固定 runner 前缀 + target + extra_args 组成。
    command_parts = list(command_prefix)

    if target and str(target).strip():
        command_parts.append(str(target).strip())

    for item in extra_args or []:
        value = str(item).strip()
        if value:
            command_parts.append(value)

    return _run_command(
        command_parts=command_parts,
        runner=runner,
        workdir=resolved_workdir,
        timeout_ms=resolved_timeout,
    )


def run_shell_command(
    command: str,
    workdir: str | None = None,
    timeout_ms: int | None = None,
) -> dict:
    """
    执行一个任意 shell 命令，支持 Windows / Linux / macOS。

    参数：
    - command (str): 要执行的 shell 命令字符串。
    - workdir (str | None): 执行命令的工作目录，默认当前目录。
    - timeout_ms (int | None): 超时时间（毫秒），默认 120000。

    返回：dict - 执行结果字典，包含 success, command, workdir, exit_code, stdout, stderr, timed_out, duration_ms 等字段。

    只接受一个字符串命令，以避免构造复杂的命令行参数列表。
    """
    if not isinstance(command, str) or not command.strip():
        return {
            "success": False,
            "error": "command must be a non-empty string",
            "code": "invalid_command",
        }

    resolved_workdir, error = _resolve_workdir(workdir)
    if error:
        return {
            "success": False,
            "error": error,
            "code": "invalid_workdir",
        }

    resolved_timeout, error = _normalize_timeout_ms(timeout_ms)
    if error:
        return {
            "success": False,
            "error": error,
            "code": "invalid_timeout",
        }

    return _run_shell_command(
        command=command.strip(),
        workdir=resolved_workdir,
        timeout_ms=resolved_timeout,
    )


def _resolve_workdir(workdir: str | None) -> tuple[Path, str | None]:
    # 默认在当前工作目录执行；这是这个工具的工作区根。
    root = Path.cwd().resolve()
    if not workdir:
        return root, None

    candidate = Path(workdir)
    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve()
        # relative_to 失败说明路径已经逃逸到工作区外面。
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        return root, f"workdir escapes workspace: {exc}"

    if not resolved.exists():
        return root, "workdir does not exist"
    if not resolved.is_dir():
        return root, "workdir is not a directory"
    return resolved, None


def _normalize_timeout_ms(timeout_ms: int | None) -> tuple[int, str | None]:
    # 不传就用默认值；传了就做类型和范围校验。
    if timeout_ms is None:
        return DEFAULT_TIMEOUT_MS, None

    try:
        value = int(timeout_ms)
    except (TypeError, ValueError):
        return 0, "timeout_ms must be an integer"

    if value <= 0:
        return 0, "timeout_ms must be greater than 0"

    return min(value, MAX_TIMEOUT_MS), None


def _run_shell_command(command: str, workdir: Path, timeout_ms: int) -> dict:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_ms / 1000,
            shell=True,
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


def _run_command(command_parts: list[str], runner: str, workdir: Path, timeout_ms: int) -> dict:
    started = time.perf_counter()
    # 这份 command 主要用于日志和结果展示，不参与执行。
    command = " ".join(command_parts)

    try:
        # shell=False 可以避免把这个工具变成任意 shell 解释器。
        completed = subprocess.run(
            command_parts,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_ms / 1000,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        # 超时属于“执行失败”，但仍然保留已经产出的部分输出。
        return {
            "success": False,
            "runner": runner,
            "command": command,
            "workdir": str(workdir),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    except OSError as exc:
        # OSError 通常表示可执行程序不存在或系统层面无法启动进程。
        return {
            "success": False,
            "runner": runner,
            "command": command,
            "workdir": str(workdir),
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }

    # returncode == 0 视为测试命令执行成功；否则交给上层判断是测试失败还是环境问题。
    return {
        "success": completed.returncode == 0,
        "runner": runner,
        "command": command,
        "workdir": str(workdir),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }


if __name__ == "__main__":
    # 测试 run_test_command
    result = run_test_command(
        runner="pytest",
        target="tests",
        extra_args=["-q"],
    )
    print("Test run_test_command:")
    print(result)

    # 测试 run_shell_command
    result_shell = run_shell_command("echo hello world", workdir=".", timeout_ms=5000)
    print("\nTest run_shell_command (echo):")
    print(result_shell)

    # 平台特定测试
    import platform
    if platform.system() == "Windows":
        result_win = run_shell_command("dir", workdir=".", timeout_ms=5000)
        print("\nTest run_shell_command (dir on Windows):")
        print(result_win)
    else:
        result_unix = run_shell_command("ls -la", workdir=".", timeout_ms=5000)
        print("\nTest run_shell_command (ls on Unix):")
        print(result_unix)
