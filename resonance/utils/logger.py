import os
import platform
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import better_exceptions
from loguru import logger

from resonance.utils import wsdata
from resonance.server.ws_state import ws_queue

from version import __version__

MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB per file


class _LogFile:
    """MowerNG 风格：活跃文件 runtime.log，超 50MB 时重命名为 runtime_YYYY-MM-DD_N.log"""
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self._path = os.path.join("logs", "runtime.log")
        self._file = None
        if os.path.exists(self._path) and os.path.getsize(self._path) > 0:
            self._rotate()
        self._file = open(self._path, "a", encoding="utf-8")

    def _rotate(self):
        today = datetime.now().strftime("%Y-%m-%d")
        seq = 1
        while True:
            archive = os.path.join("logs", f"runtime_{today}_{seq}.log")
            if not os.path.exists(archive):
                break
            seq += 1
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass
        if os.path.exists(self._path):
            os.rename(self._path, archive)
        self._file = open(self._path, "a", encoding="utf-8")

    def write(self, msg):
        if self._file.tell() + len(msg) > MAX_LOG_SIZE:
            self._rotate()
        self._file.write(msg)

    def flush(self):
        if self._file:
            self._file.flush()

    def close(self):
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass


log_handler = _LogFile()
LEVEL = "DEBUG"
logger.remove()

log_lines: list[str] = []


def _migrate_old_logs():
    """将旧格式 runtime.YYYY-MM-DD_HH-MM-SS_NNNNNN.log 重命名为 runtime_YYYY-MM-DD_1.log"""
    logs_dir = Path("logs")
    for p in sorted(logs_dir.glob("runtime.*.log")):
        parts = p.name.split(".")
        if len(parts) != 3 or parts[0] != "runtime":
            continue
        date_str = parts[1][:10]
        if not date_str[0].isdigit():
            continue
        new_name = f"runtime_{date_str}_1.log"
        new_path = logs_dir / new_name
        if not new_path.exists():
            p.rename(new_path)


def _cleanup_legacy_files():
    """Remove old-format log files (backend.log, debug*.log, error*.log, frontend.log, vite.log)."""
    logs_dir = Path("logs")
    for pat in ("backend.log", "debug*.log", "error*.log", "frontend.log", "vite.log"):
        for p in logs_dir.glob(pat):
            try:
                p.unlink()
            except OSError:
                pass
    for name in ("archive", "debug", "image"):
        d = logs_dir / name
        if d.is_dir():
            try:
                shutil.rmtree(d)
            except OSError:
                pass


def _retention_cleanup():
    """Clean up log files older than 7 days."""
    cutoff = time.time() - 7 * 86400
    for p in Path("logs").glob("runtime*log"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


_migrate_old_logs()
_retention_cleanup()
_cleanup_legacy_files()


def ws_sink(message):
    if message.record["extra"].get("skip_ws"):
        return
    msg = str(message).rstrip()
    log_lines.append(msg)
    log_lines[:] = log_lines[-100:]
    ws_queue.put(wsdata.Log(msg))


if not getattr(sys, "frozen", False):
    logger.add(
        sys.stdout,
        level=LEVEL,
        colorize=True,
        format="<cyan>{module}</cyan>.<cyan>{function}</cyan>"
        ":<cyan>{line}</cyan> - "
        "<level>{message}</level>",
    )

logger.add(
    log_handler,
    format="{time:MM-DD HH:mm:ss} {level} {message}",
    enqueue=True,
    serialize=False,
)

logger.add(
    ws_sink,
    level="INFO",
    format="{time:MM-DD HH:mm:ss} {level} {message}",
)

logger.bind(skip_ws=True).info("=" * 48)
logger.bind(skip_ws=True).info(f"启动时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
logger.bind(skip_ws=True).info(f"当前版本: {__version__}")
logger.bind(skip_ws=True).info(f"系统: {platform.system()} {platform.release()} ({platform.version()})")
logger.bind(skip_ws=True).info(f"Python: {platform.python_version()} {platform.architecture()[0]}")
logger.bind(skip_ws=True).info(f"机器: {platform.node()}")
