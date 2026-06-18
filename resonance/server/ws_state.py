"""WebSocket 连接状态管理。

独立模块，不依赖 server/app 或 routes，避免循环导入。
ws_connections / ws_lock / ws_queue / ws_push 集中管理。
"""

from threading import Lock

from resonance.utils import wsdata
from resonance.utils.queue import QueueProxy

ws_connections: list = []
ws_lock = Lock()


def ws_push(item):
    data = item.serialize()
    sub_type = item.type
    with ws_lock:
        for ws in list(ws_connections):
            if ws.push_config.get(sub_type):
                ws.send(data)


ws_queue = QueueProxy("WebSocket推送", ws_push)
