import shutil
import time
from pathlib import Path

import cv2

from resonance.utils import wsdata
from resonance.utils.logger import logger
from resonance.server.ws_state import ws_queue
from resonance.utils.queue import QueueProxy

SCREENSHOT_DIR = Path("logs") / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

ws_screenshot: bytes | None = None
_cleanup_counter = 0


def sc_worker(data):
    global _cleanup_counter
    img_bytes, filename = data
    path = SCREENSHOT_DIR / filename
    with open(path, "wb") as f:
        f.write(img_bytes)
    _cleanup_counter += 1
    if _cleanup_counter % 10 == 0:
        screenshot_cleanup()


sc_queue = QueueProxy("截图保存", sc_worker)


def save_screenshot(img):
    filename = f"{time.time_ns()}.jpg"
    _, jpeg = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if jpeg is not None:
        sc_queue.put((jpeg.tobytes(), filename))
    ws_queue.put(wsdata.Sc(img))
    logger.debug(f"[SC] {filename}")


def screenshot_cleanup():
    retention_hours = 24
    start_time_ns = time.time_ns() - retention_hours * 3600 * 10**9
    for i in SCREENSHOT_DIR.iterdir():
        if i.is_dir():
            shutil.rmtree(i)
        elif not i.stem.isnumeric():
            i.unlink()
        elif int(i.stem) < start_time_ns:
            i.unlink()


screenshot_cleanup()
