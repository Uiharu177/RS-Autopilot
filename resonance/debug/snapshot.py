"""调试快照：保存截图 + OCR + Scene + 模板匹配结果到 logs/debug/。

  被 debug API（POST /api/debug/snapshot）和 recovery模块（失败时自动保存）调用。
  每个快照包含：时间戳目录下的截图、OCR 文本文件、Scene 值、匹配结果。
"""

from pathlib import Path
import threading
import time
from typing import Any, Iterable

import cv2 as cv
from loguru import logger

from resonance.device.device import connect, screenshot_image
from resonance.scene.recognizer import Recognizer
from resonance.utils.exceptions import StopExecution
from resonance.utils.utils import RESOURCES_PATH
from resonance.vision.utils import match_template

DEBUG_DIR = Path("logs") / "debug"
_snapshot_lock = threading.Lock()


def _template_debug(frame, template_name: str, threshold: float = 0.8) -> dict[str, Any]:
    template_path = (RESOURCES_PATH / template_name).resolve()
    resources_root = RESOURCES_PATH.resolve()
    if resources_root not in template_path.parents and template_path != resources_root:
        raise ValueError(f"非法模板路径: {template_name}")
    result = match_template(frame, template_path, threshold=threshold)
    return {
        "template": template_name,
        "threshold": threshold,
        "exists": template_path.exists(),
        "matched": bool(result),
        "score": float(result.score),
        "loc": list(result.loc),
    }


def capture_debug_snapshot(
    templates: Iterable[str | dict[str, Any]] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Capture screenshot, OCR, scene and optional template matches for recovery logs."""
    if not _snapshot_lock.acquire(blocking=False):
        logger.warning(f"调试快照已在执行，跳过嵌套快照: reason={reason}")
        return {
            "success": False,
            "reentrant": True,
            "reason": reason,
            "error": "debug snapshot already in progress",
            "screenshot": None,
            "ocr_file": None,
            "ocr": [],
            "templates": [],
        }

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)

    try:
        try:
            frame = screenshot_image()
        except StopExecution:
            raise
        except Exception as e:
            logger.warning(f"调试快照截图失败，尝试重新连接设备: {e}")
            if not connect(reset_stop=False):
                raise RuntimeError("调试快照失败：设备未连接，且自动连接失败") from e
            frame = screenshot_image()
        screenshot_path = DEBUG_DIR / f"snapshot_{ts}.png"
        cv.imwrite(str(screenshot_path), frame)

        recog = Recognizer()
        recog.image = frame
        scene = recog.scene
        ocr_results = recog.ocr()

        match_results = []
        for item in templates or []:
            if isinstance(item, str):
                template_name = item
                threshold = 0.8
            elif isinstance(item, dict):
                template_name = item.get("template") or item.get("name")
                threshold = float(item.get("threshold", 0.8))
            else:
                continue
            if template_name:
                match_results.append(_template_debug(frame, template_name, threshold))

        ocr_path = DEBUG_DIR / f"ocr_{ts}.txt"
        ocr_path.write_text(
            "\n".join(
                f"[{item['text']}] score={item.get('score')} position={item.get('position')}"
                for item in ocr_results
            ),
            encoding="utf-8",
        )

        payload = {
            "success": True,
            "timestamp": ts,
            "reason": reason,
            "scene": {"name": scene.name, "value": int(scene)},
            "screenshot": str(screenshot_path).replace("\\", "/"),
            "ocr_file": str(ocr_path).replace("\\", "/"),
            "ocr": ocr_results,
            "templates": match_results,
        }
        message = (
            f"调试快照完成: reason={reason}, scene={scene.name}, "
            f"ocr={len(ocr_results)}, templates={len(match_results)}"
        )
        if reason != "frontend":
            logger.info(message)
        return payload
    finally:
        _snapshot_lock.release()
