"""Scrcpy 截图+触控方式：通过 ADB 部署 scrcpy-server，建立 H.264 视频流和控制通道。

   工作原理：
   1. 通过 ADB 推送 scrcpy-server.jar 到设备
   2. 通过 app_process 启动服务器
   3. ADB forward 建立到抽象 socket 的隧道
   4. 视频通道：读取 H.264 帧 → PyAV 解码
   5. 控制通道：二进制协议发送触控/按键事件

   支持截图和触控，不需要游戏运行即可捕获画面。
"""

import os
import socket
import struct
import subprocess
import threading
import time
from typing import Optional

import cv2 as cv
import numpy as np
from loguru import logger

from resonance.device.adb import ADB
from resonance.device.base import IADB
from resonance.model import app

SCRCPY_SERVER = "scrcpy-server-v2.7.jar"
SCRCPY_PATH = "/data/local/tmp/scrcpy-server.jar"


def _adb_path() -> str:
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


def _get_free_port() -> int:
    import socket as _socket
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _device_serial() -> str:
    return f"127.0.0.1:{getattr(app.Global.device, 'port', 16384) or 16384}"


class Scrcpy(IADB):
    def __init__(self) -> None:
        super().__init__()
        self._adb = ADB()
        self._video_sock: Optional[socket.socket] = None
        self._control_sock: Optional[socket.socket] = None
        self._frame = None
        self._frame_event = threading.Event()
        self._running = False
        self._frame_thread: Optional[threading.Thread] = None

    def connect(self, adb_port: Optional[int] = None) -> bool:
        if not self._adb.connect(adb_port):
            return False
        return self._deploy_and_start()

    def check_status(self) -> bool:
        return self._running

    def _deploy_and_start(self) -> bool:
        jar_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "resources", "vendor", SCRCPY_SERVER)
        )
        if not os.path.exists(jar_path):
            logger.error(f"scrcpy-server 不存在: {jar_path}")
            return False

        adb = _adb_path()
        serial = _device_serial()

        subprocess.run([adb, "-s", serial, "push", jar_path, SCRCPY_PATH],
                       capture_output=True, timeout=30)
        logger.info("scrcpy-server 已推送")

        cmd = (f"CLASSPATH={SCRCPY_PATH} app_process / com.genymobile.scrcpy.Server 2.7 "
               f"audio=false control=true tunnel_forward=false max_size=1920 video_codec=h264")
        subprocess.Popen(
            [adb, "-s", serial, "shell", cmd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)

        video_port = _get_free_port()
        result = subprocess.run(
            [adb, "-s", serial, "forward", f"tcp:{video_port}", "localabstract:scrcpy"],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            logger.error(f"ADB 转发失败: {result.stderr.decode().strip()}")
            return False

        try:
            self._video_sock = socket.create_connection(("127.0.0.1", video_port), timeout=10)
            dummy = self._video_sock.recv(1)
            if dummy != b"\x00":
                raise ConnectionError(f"握手数据异常: {dummy}")
        except Exception as e:
            logger.error(f"scrcpy 视频连接失败: {e}")
            return False

        ctl_port = _get_free_port()
        subprocess.run(
            [adb, "-s", serial, "forward", f"tcp:{ctl_port}", "localabstract:scrcpy"],
            capture_output=True, timeout=10,
        )
        try:
            self._control_sock = socket.create_connection(("127.0.0.1", ctl_port), timeout=10)
        except Exception as e:
            logger.warning(f"scrcpy 控制连接失败，回退 ADB 触控: {e}")

        self._running = True
        self._frame_thread = threading.Thread(target=self._read_frames, daemon=True)
        self._frame_thread.start()
        logger.info("scrcpy 连接成功")
        return True

    def _read_frames(self):
        try:
            from av.codec.context import CodecContext
            codec = CodecContext.create("h264", "r")
        except ImportError:
            logger.error("缺少 PyAV 库，无法解码 H.264 (pip install av)")
            self._running = False
            return

        while self._running:
            try:
                header = self._video_sock.recv(12)
                if len(header) < 12:
                    break
                _, size = struct.unpack("!QL", header)
                data = b""
                while len(data) < size:
                    chunk = self._video_sock.recv(min(size - len(data), 65536))
                    if not chunk:
                        break
                    data += chunk
                if len(data) < size:
                    break
                for packet in codec.parse(data):
                    for frame in codec.decode(packet):
                        self._frame = frame
                        self._frame_event.set()
            except Exception:
                break
        self._running = False

    def screenshot(self) -> Optional[cv.typing.MatLike]:
        if not self._running:
            return self._adb.screenshot()
        self._frame_event.clear()
        if self._frame_event.wait(timeout=5) and self._frame is not None:
            return self._frame.to_ndarray(format="rgb24")
        return self._adb.screenshot()

    def input_tap(self, x: int, y: int):
        if self._control_sock:
            self._scrcpy_touch(x, y, 0)
            time.sleep(0.07)
            self._scrcpy_touch(x, y, 1)
        else:
            self._adb.input_tap(x, y)

    def input_swipe(self, x1: int, y1: int, x2: int, y2: int, millisecond: int = 100):
        if self._control_sock:
            self._scrcpy_touch(x1, y1, 0)
            steps = max(int(millisecond / 10), 1)
            for i in range(1, steps):
                t = i / steps
                self._scrcpy_touch(int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t), 2)
                time.sleep(0.01)
            self._scrcpy_touch(x2, y2, 1)
        else:
            self._adb.input_swipe(x1, y1, x2, y2, millisecond)

    def _scrcpy_touch(self, x: int, y: int, action: int):
        x, y = max(x, 0), max(y, 0)
        if action == 0:
            actions_button, buttons = 1, 1
        elif action == 1:
            actions_button, buttons = 1, 0
        else:
            actions_button, buttons = 0, 1
        msg = struct.pack("!B", 2) + struct.pack(
            "!BqIIHHHII", action, -1, int(x), int(y), 1920, 1080, 0xFFFF, actions_button, buttons,
        )
        try:
            self._control_sock.sendall(msg)
        except Exception:
            pass

    def kill(self):
        self._running = False
        for s in [self._video_sock, self._control_sock]:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
        serial = _device_serial()
        subprocess.run([_adb_path(), "-s", serial, "shell", "pkill -f scrcpy"],
                       capture_output=True)
        self._video_sock = None
        self._control_sock = None
        self._adb.kill()
