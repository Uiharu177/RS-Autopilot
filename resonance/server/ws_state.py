"""WebSocket 连接状态管理。

独立模块，不依赖 server/app 或 routes，避免循环导入。
ws_connections / ws_lock / ws_queue / ws_push 集中管理。
"""

from threading import Lock

from resonance.utils import wsdata
from resonance.utils.queue import LatestValueProxy, QueueProxy

ws_connections: list = []
ws_lock = Lock()


def ws_push(item):
    data = item.serialize()
    sub_type = item.type
    dead = []
    with ws_lock:
        for ws in ws_connections:
            if ws.push_config.get(sub_type):
                try:
                    ws.send(data)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            ws_connections.remove(ws)


def has_ws_subscribers(sub_type: str) -> bool:
    """Return whether at least one live client requested a message type."""
    with ws_lock:
        return any(ws.push_config.get(sub_type) for ws in ws_connections)


# Logs are ordered and use a larger buffer. Screenshot previews are lossy by
# design: only the newest frame matters, so they use a separate latest-value
# worker and can never crowd logs out of the queue.
ws_log_queue = QueueProxy("WebSocket日志推送", ws_push, maxsize=256)
# Four frames per second keeps the dashboard responsive while avoiding visual
# lag and unnecessary JPEG work during OCR-heavy automation.
ws_screenshot_queue = LatestValueProxy(ws_push, min_interval=0.25)
