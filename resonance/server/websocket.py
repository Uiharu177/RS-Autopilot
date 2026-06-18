import json

from simple_websocket import ConnectionClosed

from resonance.server.app import app, sock
from resonance.server.ws_state import ws_connections, ws_lock
from resonance.utils import wsdata
from resonance.utils.logger import logger


@sock.route("/wsecho")
def wsecho(ws):
    data = ws.receive()
    ws.send('echo:' + str(data))


@sock.route("/ws")
def log(ws):
    ws.push_config = {}

    with ws_lock:
        ws_connections.append(ws)

    try:
        raw = ws.receive()
        ws.push_config.update(json.loads(raw))

        for msg_cls in wsdata.WsMsg.data_types:
            if ws.push_config.get(msg_cls.type):
                if data := msg_cls.construct_initial():
                    try:
                        ws.send(data)
                    except Exception as e:
                        logger.warning(f"WS发送初始数据失败({msg_cls.type}): {e}")

        while True:
            raw = ws.receive()
            ws.push_config.update(json.loads(raw))
    except ConnectionClosed:
        pass
    except Exception as e:
        logger.warning(f"WS handler异常: {type(e).__name__}: {e}")
    finally:
        with ws_lock:
            if ws in ws_connections:
                ws_connections.remove(ws)
