#!/usr/bin/env python3
"""
一键启动 FastAPI + Vite 前端（自动加载 .env）
"""

from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"
WEBSITE_DIR = ROOT_DIR / "website"


def load_environment() -> None:
    """尝试加载 .env，用于本地开发。"""
    if not ENV_FILE.exists():
        print(f"[warn] 未找到 {ENV_FILE}，请确认环境变量配置。", file=sys.stderr)
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[warn] 未安装 python-dotenv，执行 `pip install python-dotenv` 可自动加载 .env。", file=sys.stderr)
        return

    load_dotenv(ENV_FILE)


def spawn_process(command: list[str], cwd: Path | None = None) -> subprocess.Popen:
    """启动子进程，若失败则抛出异常。"""
    try:
        return subprocess.Popen(command, cwd=cwd or ROOT_DIR)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"启动命令失败：{' '.join(command)}，请确认依赖已安装。") from exc


def main() -> int:
    load_environment()

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "holisticaquant.api.server:app",
        "--reload",
    ]
    if ENV_FILE.exists():
        backend_cmd.extend(["--env-file", str(ENV_FILE)])

    frontend_cmd = ["npm", "--prefix", str(WEBSITE_DIR), "run", "dev"]

    processes: list[subprocess.Popen] = []

    def terminate_processes(*_args) -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    signal.signal(signal.SIGINT, terminate_processes)
    signal.signal(signal.SIGTERM, terminate_processes)

    try:
        backend_proc = spawn_process(backend_cmd, cwd=ROOT_DIR)
        processes.append(backend_proc)
        print("[info] FastAPI 已启动，监听默认 8000 端口。")

        frontend_proc = spawn_process(frontend_cmd, cwd=ROOT_DIR)
        processes.append(frontend_proc)
        print("[info] Vite 正在启动，默认访问 http://localhost:5173")

        backend_proc.wait()
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 启动失败：{exc}", file=sys.stderr)
        terminate_processes()
        return 1
    finally:
        terminate_processes()

    return 0


if __name__ == "__main__":
    sys.exit(main())

