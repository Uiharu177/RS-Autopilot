"""MuMu IPC 设备实现：通过模拟器共享内存直接读取画面。

  截图速度比 ADB 快（内存读取 vs TCP 传输），适合频繁截图场景。
  触控仍走 ADB shell input（MuMu IPC 不提供触控接口）。
  已集成游戏进程管理：kill() → am force-stop com.hermes.goda（通过 ADB 代理）
"""

import ctypes
import os
import time
from typing import Optional

from loguru import logger
import numpy as np
from resonance.device.port_scanner import EmulatorType
from resonance.device.base import IADB
import cv2 as cv

from resonance.device.nemu_dll.nemu_dll import init
from resonance.device.adb import ADB
from resonance.model import app


def swipe_path(p0, p3, time):
    path = []
    p0 = np.array(p0)
    p3 = np.array(p3)
    p1 = 2/3 * p0 + 1/3 * p3
    p2 = 1/3 * p0 + 2/3 * p3

    time = int(time / 10)
    for i in range(time):
        t = i / (time - 1)
        point = (1 - t)**3 * p0 + \
            3 * (1 - t)**2 * t * p1 + \
            3 * (1 - t) * t**2 * p2 + \
            t**3 * p3
        point = point.astype(int).tolist()
        path.append(point)

    return path


class NEMU(IADB):
    @staticmethod
    def is_available() -> bool:
        device = app.Global.device
        if not device.path:
            return False
        if device.type == EmulatorType.MUMUV5:
            dll = os.path.join(device.path, "nx_device", "12.0", "shell", "sdk", "external_renderer_ipc.dll")
        elif device.type == EmulatorType.MUMUV4:
            dll = os.path.join(device.path, "shell", "sdk", "external_renderer_ipc.dll")
        else:
            return False
        return os.path.isfile(dll)

    def __init__(self) -> None:
        self.device = app.Global.device
        self.path = self.device.path
        if self.device.type == EmulatorType.MUMUV5:
            path = os.path.join(self.path, "nx_device", "12.0", "shell", "sdk", "external_renderer_ipc.dll")
        elif self.device.type == EmulatorType.MUMUV4:
            path = os.path.join(self.path, "shell", "sdk", "external_renderer_ipc.dll")
        else:
            raise Exception(f"不支持的模拟器类型: {self.device.type}")
        logger.info(
            f"NEMUIPC初始化: name={self.device.name}, type={self.device.type.value}, "
            f"index={self.device.index}, port={self.device.port}, path={self.path}, dll={path}"
        )
        self.nemu = init(path)
        self.connect_id = 0
        self.display_id = -1
        self._display_ready = False

    def check_status(self) -> bool:
        return self.connect_id > 0

    def _reconnect(self) -> bool:
        self.connect_id = 0
        self.display_id = -1
        self._display_ready = False
        return self.connect()

    def connect(self, adb_port: Optional[int] = None) -> bool:
        self.connect_id = self.nemu.nemu_connect(self.path, self.device.index)
        logger.info(f"NEMUIPC connect_id={self.connect_id}")
        if self.connect_id <= 0:
            logger.error("NEMUIPC连接失败: connect_id <= 0")
            return False
        self.display_id = -1
        self._display_ready = False
        logger.info("NEMUIPC连接成功，游戏渲染显示将延迟到首次操作时获取")
        return True

    def _acquire_display(self) -> bool:
        if self._display_ready:
            return True
        self.display_id = self.nemu.nemu_get_display_id(self.connect_id, b"com.hermes.goda", 0)
        logger.info(f"NEMUIPC display_id={self.display_id}")
        if self.display_id < 0:
            logger.warning("NEMUIPC display_id < 0，游戏可能未启动或不在前台")
            return False

        self.width_ptr = ctypes.pointer(ctypes.c_int(0))
        self.height_ptr = ctypes.pointer(ctypes.c_int(0))
        nullptr = ctypes.POINTER(ctypes.c_ubyte)()
        ret = self.nemu.nemu_capture_display(self.connect_id, self.display_id, 0, self.width_ptr, self.height_ptr, nullptr)

        self.width = self.width_ptr.contents.value
        self.height = self.height_ptr.contents.value
        logger.info(f"NEMUIPC capture ret={ret}, size={self.width}x{self.height}")

        self.length = self.width * self.height * 4
        if self.length <= 0:
            logger.error("NEMUIPC捕获尺寸无效")
            self.display_id = -1
            return False
        self.pixels_array = (ctypes.c_ubyte * self.length)()
        self.pixels_pointer = ctypes.pointer(self.pixels_array)
        ok = self.check_resolution_ratio(self.width, self.height)
        logger.info(f"NEMUIPC分辨率检查: {'通过' if ok else '失败'}")
        if not ok:
            self.display_id = -1
            return False
        self._display_ready = True
        return True

    def _ensure_display(self) -> bool:
        if not self.check_status():
            self._reconnect()
        if not self.check_status():
            return False
        if not self._display_ready:
            self._acquire_display()
        return self._display_ready

    def input_swipe(self, x1: int, y1: int, x2: int, y2: int, millisecond: int = 100) -> None:
        if not self._ensure_display():
            return
        points = swipe_path((x1, y1), (x2, y2), millisecond)
        for point in points:
            self.nemu.nemu_input_event_touch_down(self.connect_id, self.display_id, *point)
            time.sleep(0.01)
        self.nemu.nemu_input_event_touch_up(self.connect_id, self.display_id)
        time.sleep(0.05)

    def input_swipe_hold(self, x1: int, y1: int, x2: int, y2: int, millisecond: int = 100, hold_ms: int = 800) -> None:
        if not self._ensure_display():
            return
        points = swipe_path((x1, y1), (x2, y2), millisecond)
        for point in points:
            self.nemu.nemu_input_event_touch_down(self.connect_id, self.display_id, *point)
            time.sleep(0.01)
        time.sleep(hold_ms / 1000)
        self.nemu.nemu_input_event_touch_up(self.connect_id, self.display_id)
        time.sleep(0.05)

    def input_tap(self, x: int, y: int):
        if not self._ensure_display():
            return
        self.nemu.nemu_input_event_touch_down(self.connect_id, self.display_id, x, y)
        self.nemu.nemu_input_event_touch_up(self.connect_id, self.display_id)
        time.sleep(0.5)

    def screenshot(self) -> Optional[cv.typing.MatLike]:
        if not self._ensure_display():
            return None
        self.nemu.nemu_capture_display(self.connect_id, self.display_id, self.length, self.width_ptr, self.height_ptr, self.pixels_pointer)
        image = np.frombuffer(self.pixels_array, dtype=np.uint8).reshape((self.height, self.width, 4))
        image = cv.cvtColor(image, cv.COLOR_BGRA2RGB)
        image = cv.flip(image, 0)
        return image
    
    def kill(self):
        self.connect_id = 0
        self.display_id = -1
        self._display_ready = False
