"""ADB TCP 设备实现：通过 adb-shell 库连接模拟器 ADB 端口。

  提供截图（/dev/input/event* 或 framebuffer）和触控（input tap/swipe）。
  截图方式支持默认（adb exec-out screencap）和 JPG 模式。
"""

import time
from typing import Optional

import cv2 as cv
from loguru import logger
import numpy as np
from resonance.device.base import IADB
from adb_shell.adb_device import AdbDeviceTcp

from resonance.model import app

PNG_KEY = b"\x89PNG"


class ADB(IADB):
    def __init__(self) -> None:
        super().__init__()
        self.adb_host = "127.0.0.1"
        self.device = AdbDeviceTcp(self.adb_host)
        self._adb_port: Optional[int] = None
        self._adb_connected = False

    def connect(self, adb_port: Optional[int] = None) -> bool:
        name = "自定义ADB端口"
        if adb_port is None:
            device = app.Global.device
            adb_port = device.port
            name = device.name
        if adb_port is None:
            logger.info(f"未知ADB端口信息 {name}，请检测ADB端口是否设置正确")
            return False
        self._adb_port = adb_port
        logger.info(f"ADB端口：{name}-{adb_port}")
        self.device = AdbDeviceTcp(self.adb_host, port=adb_port)
        try:
            status = self.device.connect()
            if not status:
                logger.error("ADB连接失败")
            else:
                image = self.screenshot()
                height, width = image.shape[:2]
                ok = self.check_resolution_ratio(width, height)
                if ok:
                    self._adb_connected = True
                return ok
        except ConnectionRefusedError:
            status = False
            logger.error("ADB端口错误或者未打开模拟器，无法连接")
        self._adb_connected = False
        return status

    def check_status(self) -> bool:
        if not self._adb_connected:
            return self._reconnect()
        try:
            self.device.shell("echo 1")
            return True
        except Exception:
            self._adb_connected = False
            return self._reconnect()

    def _reconnect(self) -> bool:
        if self._adb_port is None:
            return False
        try:
            self.device = AdbDeviceTcp(self.adb_host, port=self._adb_port)
            status = self.device.connect()
            if status:
                self._adb_connected = True
                return True
        except Exception:
            pass
        self._adb_connected = False
        return False

    def input_swipe(self, x1: int, y1: int, x2: int, y2: int, millisecond: int = 100) -> None:
        if not self.check_status():
            return
        shell = [
            "input",
            "swipe",
            f"{x1} {y1} {x2} {y2}",
            f"{millisecond}",
        ]
        self.device.shell(" ".join(shell))
        time.sleep(millisecond / 1000)

    def input_tap(self, x: int, y: int):
        if not self.check_status():
            return
        shell = [
            "input",
            "tap",
            str(x),
            str(y),
        ]
        self.device.shell(" ".join(shell))

    def input_keyevent(self, keycode: int):
        if not self.check_status():
            return
        self.device.shell(f"input keyevent {keycode}")

    def screenshot(self) -> cv.typing.MatLike:
        if not self.check_status():
            raise ConnectionError("ADB未连接，无法截图")
        screenshot_data = self.device.shell("screencap -p", decode=False)
        if isinstance(screenshot_data, str):
            raise Exception(f"无法获取屏幕截图: {screenshot_data}")
        if screenshot_data[:4] != PNG_KEY:
            index = screenshot_data.find(PNG_KEY)
            if index == -1:
                raise Exception("无法获取屏幕截图: 截图数据不包含PNG头")
            screenshot_data = screenshot_data[index:]

        image_array = np.frombuffer(screenshot_data, np.uint8)
        screenshot = cv.imdecode(image_array, cv.IMREAD_COLOR)
        return screenshot

    def kill(self):
        self._adb_connected = False
        if self.device is None:
            return
        try:
            self.device.close()
        except Exception:
            logger.exception("关闭 ADB 连接失败")
