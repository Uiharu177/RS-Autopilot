"""设备控制统一接口：连接、截图、触控、游戏进程管理。

  根据配置自动选择 ADB / MuMu IPC 作为截图后端。
  提供全局 STOP 标志，截图操作检测到 STOP=True 时抛出 StopExecution。
  提供便捷函数：connect() / screenshot() / input_tap() / input_swipe()
                   start_game() / stop_game() / restart_game() / kill()
"""

import random
import time
from typing import Dict, List, Optional, Tuple

import cv2 as cv
import numpy as np
from loguru import logger

from resonance.device.adb import ADB
from resonance.device.base import IADB
from resonance.device.nemu import NEMU
from resonance.device.droidcast import DroidCast
from resonance.device.scrcpy import Scrcpy
from resonance.device.port_scanner import EmulatorType
from resonance.utils.exceptions import StopExecution
from resonance.vision.image import Image
from resonance.model import app
from resonance.model.runtime import ScreenshotMethod

EXCURSIONX = [-10, 10]
EXCURSIONY = [-10, 10]
STOP = False

_device: IADB = ADB()
_is_connected = False


def get_device() -> IADB:
    global _device
    return _device


def launch_emulator(port: int = 0) -> bool:
    """Launch MuMu emulator and wait for it to be ready. Only uses port to look up index."""
    import subprocess
    import json
    cfg = app.Global
    mm_path = cfg.device.path
    if not mm_path:
        logger.error("未配置模拟器路径")
        return False
    manager = mm_path + "\\nx_main\\MuMuManager.exe"
    import os
    if not os.path.exists(manager):
        logger.error(f"MuMuManager not found: {manager}")
        return False
    # Find instance index by port
    try:
        r = subprocess.run([manager, "info", "-v", "all"], capture_output=True,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode == 0 and r.stdout:
            text = r.stdout.decode("utf-8", errors="replace")
            info = json.loads(text)
            target = None
            for idx, inst in info.items():
                if inst.get("adb_port") == port or inst.get("index") == str(cfg.device.index):
                    target = idx
                    break
            if target is not None and info[target].get("player_state") == "start_finished":
                logger.info(f"模拟器实例 {target} 已在运行")
                return True
        index = port - 16384 if port >= 16384 else cfg.device.index
        logger.info(f"启动模拟器实例 {index}...")
        subprocess.run([manager, "control", "--vmindex", str(index), "launch"],
                      capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for i in range(60):
            time.sleep(2)
            r = subprocess.run([manager, "info", "-v", "all"], capture_output=True,
                              creationflags=subprocess.CREATE_NO_WINDOW)
            if r.returncode == 0 and r.stdout:
                try:
                    text = r.stdout.decode("utf-8", errors="replace")
                    info = json.loads(text)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if info.get(str(index), {}).get("player_state") == "start_finished":
                    logger.info(f"模拟器实例 {index} 启动完成 ({(i+1)*2}s)")
                    return True
        logger.error(f"模拟器实例 {index} 启动超时")
        return False
    except Exception as e:
        logger.exception(f"启动模拟器失败: {e}")
        return False


def connect(port: Optional[int] = None, reset_stop: bool = True, max_retries: int = 3, force: bool = False):
    global _device, STOP, _is_connected
    if reset_stop:
        STOP = False
    cfg = app.Global

    if port is not None:
        cfg.device.port = port

    actual_port = port or cfg.device.port
    touch = getattr(cfg.touch_method, "value", cfg.touch_method)
    screenshot = getattr(cfg.screenshot_method, "value", cfg.screenshot_method)

    if _is_connected and not force:
        return True

    for attempt in range(1, max_retries + 1):
        logger.info(f"连接设备 ({attempt}/{max_retries}) port={actual_port}")
        device = _pick_device(touch, screenshot)
        try:
            status = device.connect(actual_port)
            if status:
                _device = device
                _is_connected = True
                return True
        except Exception as e:
            logger.warning(f"{device.__class__.__name__}连接失败: {e}")

        logger.warning(f"{device.__class__.__name__}连接失败，回退到ADB")
        _device = ADB()
        status = _device.connect(actual_port)
        if status:
            _is_connected = True
            return True
        if attempt < max_retries:
            time.sleep(3)
    _is_connected = False
    logger.error(f"设备连接失败，重试 {max_retries} 次后放弃")
    return False


def _pick_device(touch: str, screenshot: str) -> IADB:
    if touch == "scrcpy" or screenshot == "scrcpy":
        return Scrcpy()
    if touch == "nemu" or screenshot == "nemu":
        if NEMU.is_available():
            return NEMU()
        logger.warning("NEMU IPC 不可用（未检测到模拟器路径或 DLL），回退到 ADB")
    if screenshot == "droidcast":
        return DroidCast()
    return ADB()


def benchmark_screenshot_methods(
    port: Optional[int] = None,
    samples: int = 5,
    warmup: int = 1,
    apply_fastest: bool = False,
) -> Dict:
    """Measure available screenshot backends and optionally persist the fastest one."""
    cfg = app.Global
    actual_port = port or cfg.device.port
    original_device = cfg.device
    scanned_device = None
    methods = [ScreenshotMethod.ADB]
    if NEMU.is_available():
        methods.append(ScreenshotMethod.NEMU)
    methods.append(ScreenshotMethod.SCRCPY)
    methods.append(ScreenshotMethod.DROIDCAST)
    results: List[Dict] = []

    for method in methods:
        device = None
        item = {
            "method": method.value,
            "ok": False,
            "avg_ms": None,
            "min_ms": None,
            "max_ms": None,
            "samples": [],
            "error": None,
        }
        try:
            if method == ScreenshotMethod.ADB:
                device = ADB()
            elif method == ScreenshotMethod.NEMU:
                device = NEMU()
            elif method == ScreenshotMethod.SCRCPY:
                device = Scrcpy()
            elif method == ScreenshotMethod.DROIDCAST:
                device = DroidCast()
            else:
                item["error"] = "unknown method"
                results.append(item)
                continue
            if not device.connect(actual_port):
                item["error"] = "connect failed"
                results.append(item)
                continue

            for _ in range(max(0, warmup)):
                device.screenshot()

            durations = []
            for _ in range(max(1, samples)):
                start = time.perf_counter()
                image = device.screenshot()
                elapsed_ms = (time.perf_counter() - start) * 1000
                if image is None or image.size == 0:
                    raise RuntimeError("empty screenshot")
                durations.append(round(elapsed_ms, 2))

            item.update({
                "ok": True,
                "avg_ms": round(sum(durations) / len(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "samples": durations,
            })
        except Exception as e:
            logger.warning(f"截图测速失败: {method.value} ({e})")
            item["error"] = str(e)
        finally:
            cfg.device = original_device
            if device is not None:
                try:
                    device.kill()
                except Exception:
                    logger.debug(f"关闭截图测速设备失败: {method.value}")
            results.append(item)

    successful = [item for item in results if item["ok"]]
    fastest = min(successful, key=lambda item: item["avg_ms"]) if successful else None

    if apply_fastest and fastest:
        if fastest["method"] == ScreenshotMethod.NEMU.value and scanned_device is not None:
            cfg.device = scanned_device
        cfg.screenshot_method = ScreenshotMethod(fastest["method"])
        app.save_config()
        logger.info(f"已选择最快截图方式: {fastest['method']} ({fastest['avg_ms']}ms)")

    return {
        "success": bool(successful),
        "fastest": fastest["method"] if fastest else None,
        "applied": bool(apply_fastest and fastest),
        "results": results,
    }


def stop():
    global STOP
    STOP = True


def kill():
    global _is_connected
    _device.kill()
    _is_connected = False
    adb = _adb_for_game_action("强制关闭")
    if adb is None:
        return
    try:
        adb.device.shell(f"am force-stop {PACKAGE_NAME}")
        logger.info("游戏进程已关闭")
    except Exception:
        logger.exception("kill: 强制关闭游戏失败")
    finally:
        adb.kill()


PACKAGE_NAME = "com.hermes.goda"


def _adb_for_game_action(action_name: str):
    adb = ADB()
    port = app.Global.device.port
    if not port:
        logger.error(f"未配置ADB端口，无法{action_name}游戏")
        return None

    status = adb.connect(port)
    if not status:
        logger.error(f"ADB连接失败，无法{action_name}游戏")
        adb.kill()
        return None
    return adb


def _get_focus_from_connected_adb(adb: ADB) -> Optional[str]:
    commands = [
        "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'",
        "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'",
    ]
    for command in commands:
        result = adb.device.shell(command)
        if result:
            return str(result).strip()
    return None


def stop_game() -> Dict:
    adb = _adb_for_game_action("关闭")
    if adb is None:
        return {"success": False, "action": "stop", "error": "ADB连接失败或端口未配置"}

    try:
        logger.info(f"正在关闭游戏 {PACKAGE_NAME}...")
        adb.device.shell(f"am force-stop {PACKAGE_NAME}")
        time.sleep(2)
        return {"success": True, "action": "stop", "package": PACKAGE_NAME}
    except Exception as e:
        logger.exception("关闭游戏失败")
        return {"success": False, "action": "stop", "error": str(e)}
    finally:
        adb.kill()


def start_game() -> Dict:
    adb = _adb_for_game_action("启动")
    if adb is None:
        return {"success": False, "action": "start", "error": "ADB连接失败或端口未配置"}

    try:
        logger.info(f"正在启动游戏 {PACKAGE_NAME}...")
        output = adb.device.shell(f"monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1")
        logger.info(f"启动游戏输出: {str(output).strip()}")
        time.sleep(3)
        focus = _get_focus_from_connected_adb(adb)
        if focus and PACKAGE_NAME in focus:
            logger.info("游戏启动成功，已在前台")
            return {"success": True, "action": "start", "package": PACKAGE_NAME, "focus": focus, "output": output}
        logger.error(f"游戏启动后未进入前台，当前前台: {focus or 'unknown'}")
        return {
            "success": False,
            "action": "start",
            "package": PACKAGE_NAME,
            "focus": focus,
            "output": output,
            "error": f"游戏启动后未进入前台: {focus or 'unknown'}",
        }
    except Exception as e:
        logger.exception("启动游戏失败")
        return {"success": False, "action": "start", "error": str(e)}
    finally:
        adb.kill()


def get_current_focus() -> Optional[str]:
    adb = _adb_for_game_action("读取前台应用")
    if adb is None:
        return None

    try:
        return _get_focus_from_connected_adb(adb)
    except Exception as e:
        logger.warning(f"读取前台应用失败: {e}")
        return None
    finally:
        adb.kill()


def is_game_foreground() -> bool:
    focus = get_current_focus()
    if not focus:
        return False
    return PACKAGE_NAME in focus


def ensure_game_foreground() -> bool:
    focus = get_current_focus()
    if focus and PACKAGE_NAME in focus:
        logger.info("游戏已在前台")
        return True

    logger.info(f"游戏不在前台，当前前台: {focus or 'unknown'}")
    result = start_game()
    return bool(result.get("success"))


def restart_game(timeout=120):
    stop_result = stop_game()
    if not stop_result["success"]:
        return False
    start_result = start_game()
    return start_result["success"]


def _ensure_connected():
    if STOP:
        return
    if not _device.check_status():
        logger.warning("设备连接已断开，尝试重连")
        connect(force=True, reset_stop=False)


def input_swipe(pos1=(919, 617), pos2=(919, 908), swipe_time: int = 100):
    _ensure_connected()
    num = 0
    pos_x1 = _device.ratio * pos1[0] + random.randint(*EXCURSIONX)
    pos_y1 = _device.ratio * pos1[1] + random.randint(*EXCURSIONY)
    pos_x2 = _device.ratio * pos2[0] + random.randint(*EXCURSIONX)
    pos_y2 = _device.ratio * pos2[1] + random.randint(*EXCURSIONY)

    while abs(pos_x2 - pos_x1) > 10 or abs(pos_y2 - pos_y1) > 10:
        if num >= 1:
            time.sleep(0.5)
        limit_pos_x1 = max(_device.safe_area[0], min(pos_x1, _device.safe_area[2]))
        limit_pos_y1 = max(_device.safe_area[1], min(pos_y1, _device.safe_area[3]))
        limit_pos_x2 = max(_device.safe_area[0], min(pos_x2, _device.safe_area[2]))
        limit_pos_y2 = max(_device.safe_area[1], min(pos_y2, _device.safe_area[3]))

        _device.input_swipe(limit_pos_x1, limit_pos_y1, limit_pos_x2, limit_pos_y2, swipe_time)

        pos_x1 -= limit_pos_x1 - limit_pos_x2
        pos_y1 -= limit_pos_y1 - limit_pos_y2
        num += 1


def input_swipe_hold(pos1=(919, 617), pos2=(919, 908), swipe_time: int = 100, hold_ms: int = 800):
    _ensure_connected()
    pos_x1 = _device.ratio * pos1[0] + random.randint(*EXCURSIONX)
    pos_y1 = _device.ratio * pos1[1] + random.randint(*EXCURSIONY)
    pos_x2 = _device.ratio * pos2[0] + random.randint(*EXCURSIONX)
    pos_y2 = _device.ratio * pos2[1] + random.randint(*EXCURSIONY)
    limit_pos_x1 = max(_device.safe_area[0], min(pos_x1, _device.safe_area[2]))
    limit_pos_y1 = max(_device.safe_area[1], min(pos_y1, _device.safe_area[3]))
    limit_pos_x2 = max(_device.safe_area[0], min(pos_x2, _device.safe_area[2]))
    limit_pos_y2 = max(_device.safe_area[1], min(pos_y2, _device.safe_area[3]))

    if hasattr(_device, "input_swipe_hold"):
        _device.input_swipe_hold(limit_pos_x1, limit_pos_y1, limit_pos_x2, limit_pos_y2, swipe_time, hold_ms)
        return

    _device.input_swipe(limit_pos_x1, limit_pos_y1, limit_pos_x2, limit_pos_y2, swipe_time)
    _device.input_swipe(limit_pos_x2, limit_pos_y2, limit_pos_x2, limit_pos_y2, hold_ms)


def input_tap(pos: Tuple[int, int] = (880, 362)):
    _ensure_connected()
    _device.input_tap(
        int(_device.ratio * pos[0] + random.randint(*EXCURSIONX)),
        int(_device.ratio * pos[1] + random.randint(*EXCURSIONY)),
    )


def input_back():
    if hasattr(_device, "input_keyevent"):
        _device.input_keyevent(4)
        return

    adb = _adb_for_game_action("发送返回键")
    if adb is None:
        return
    try:
        adb.device.shell("input keyevent 4")
    finally:
        adb.kill()


def screenshot() -> Image:
    if STOP:
        raise StopExecution()
    return Image(screenshot_image())


def screenshot_image() -> cv.typing.MatLike:
    _ensure_connected()
    if STOP:
        raise StopExecution()
    screenshot = _device.screenshot()
    if screenshot is None:
        adb = ADB()
        adb.connect()
        screenshot = adb.screenshot()
    screenshot = cv.resize(screenshot, _device.dsize, interpolation=cv.INTER_AREA)
    from resonance.utils.screenshot_logger import save_screenshot

    save_screenshot(screenshot)
    return screenshot


def wait_stopped(threshold=7100000):
    logger.info("等待图像静止")
    while True:
        gray1 = cv.cvtColor(screenshot_image(), cv.COLOR_BGR2GRAY)
        time.sleep(0.5)
        gray2 = cv.cvtColor(screenshot_image(), cv.COLOR_BGR2GRAY)
        diff = cv.absdiff(gray1, gray2)
        diff_sum: int = np.sum(diff)
        logger.debug(f"画面差异 {diff_sum}")
        if diff_sum < threshold:
            break
        time.sleep(1)
