"""DroidCast 截图方式：通过 ADB 部署 HTTP 截图服务器。

   工作原理：
   1. 通过 ADB 安装 DroidCast-debug APK（首次运行）
   2. 通过 ADB 启动 app_process 运行 DroidCast 主类
   3. ADB 端口转发到本地端口
   4. HTTP GET 请求获取截图（比 ADB screencap 更快）

   触控委托给 ADB。
"""

import os
import subprocess
import time
from typing import Optional

import cv2 as cv
import numpy as np
import requests

from loguru import logger

from resonance.device.adb import ADB
from resonance.device.base import IADB
from resonance.model import app

DROIDCAST_PACKAGE = "com.rayworks.droidcast"
DROIDCAST_PORT = 53516


def _adb_path() -> str:
    """Find the ADB executable path."""
    path = getattr(app.Global.device, "path", None)
    if path:
        adb_in_path = os.path.join(path, "adb.exe")
        if os.path.exists(adb_in_path):
            return adb_in_path
    for candidate in ["adb.exe", "adb"]:
        try:
            subprocess.run([candidate, "version"], capture_output=True, text=True, timeout=5)
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "adb.exe"


class DroidCast(IADB):
    def __init__(self) -> None:
        super().__init__()
        self._adb = ADB()
        self._server_port = 0
        self._session = requests.Session()

    def connect(self, adb_port: Optional[int] = None) -> bool:
        if not self._adb.connect(adb_port):
            return False
        self._ensure_server()
        return True

    def check_status(self) -> bool:
        if not self._adb.check_status():
            return False
        if self._server_port == 0:
            return False
        try:
            self._session.get(f"http://127.0.0.1:{self._server_port}/screenshot", timeout=3)
            return True
        except requests.RequestException:
            return self._ensure_server()

    def _ensure_server(self) -> bool:
        return self._install_if_needed() and self._start_server()

    def _install_if_needed(self) -> bool:
        out = self._adb.device.shell(f"pm path {DROIDCAST_PACKAGE}")
        if DROIDCAST_PACKAGE in out:
            logger.debug("DroidCast 已安装")
            return True
        logger.info("安装 DroidCast...")
        apk_path = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "vendor", "DroidCast-debug-1.2.1.apk")
        apk_path = os.path.normpath(apk_path)
        if not os.path.exists(apk_path):
            logger.error(f"DroidCast APK 不存在: {apk_path}")
            return False
        port = app.Global.device.port or adb_port_global()
        result = subprocess.run(
            [_adb_path(), "-s", f"127.0.0.1:{port}", "install", "-r", "-t", apk_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"DroidCast 安装失败: {result.stderr}")
            return False
        logger.info("DroidCast 安装成功")
        return True

    def _start_server(self) -> bool:
        port = app.Global.device.port or adb_port_global()
        adb = _adb_path()

        out = self._adb.device.shell(f"pm path {DROIDCAST_PACKAGE}")
        classpath = None
        for line in out.splitlines():
            if line.startswith("package:"):
                classpath = "CLASSPATH=" + line[len("package:"):].strip()
                break
        if not classpath:
            logger.error("无法获取 DroidCast CLASSPATH")
            return False

        subprocess.run(
            [adb, "-s", f"127.0.0.1:{port}", "forward", f"tcp:{DROIDCAST_PORT}", f"tcp:{DROIDCAST_PORT}"],
            capture_output=True, timeout=10,
        )
        logger.info(f"ADB 端口转发 {DROIDCAST_PORT} -> {DROIDCAST_PORT}")

        cmd = f"{classpath} app_process / {DROIDCAST_PACKAGE}.Main --port={DROIDCAST_PORT}"
        self._adb.device.shell(f"nohup {cmd} > /dev/null 2>&1 &")
        time.sleep(2)

        self._server_port = DROIDCAST_PORT
        try:
            r = self._session.get(f"http://127.0.0.1:{self._server_port}/screenshot", timeout=5)
            if r.status_code == 200:
                logger.info("DroidCast 服务器启动成功")
                return True
        except requests.RequestException:
            pass
        logger.warning("DroidCast 服务器启动失败")
        self._server_port = 0
        return False

    def screenshot(self) -> Optional[cv.typing.MatLike]:
        if self._server_port == 0:
            return self._adb.screenshot()
        try:
            r = self._session.get(f"http://127.0.0.1:{self._server_port}/screenshot", timeout=10)
            if r.status_code != 200:
                return self._adb.screenshot()
            img_array = np.frombuffer(r.content, dtype=np.uint8)
            img = cv.imdecode(img_array, cv.IMREAD_COLOR)
            if img is None:
                return self._adb.screenshot()
            return cv.cvtColor(img, cv.COLOR_BGR2RGB)
        except requests.RequestException:
            return self._adb.screenshot()

    def input_tap(self, x: int, y: int):
        self._adb.input_tap(x, y)

    def input_swipe(self, x1: int, y1: int, x2: int, y2: int, millisecond: int = 100):
        self._adb.input_swipe(x1, y1, x2, y2, millisecond)

    def kill(self):
        if self._server_port:
            try:
                self._session.get(f"http://127.0.0.1:{self._server_port}/stop", timeout=2)
            except requests.RequestException:
                pass
            self._adb.device.shell(f"pkill -f {DROIDCAST_PACKAGE}")
        self._server_port = 0
        self._adb.kill()


def adb_port_global() -> int:
    return getattr(app.Global.device, "port", 16384) or 16384
