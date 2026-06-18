from flask import Blueprint, jsonify, request

from resonance.device.device import benchmark_screenshot_methods, connect, get_device, restart_game, start_game, stop_game
from resonance.device.adb import ADB
from resonance.device.nemu import NEMU
from resonance.model.runtime import app
from resonance.device.port_scanner import get_adb_port
from loguru import logger

device_bp = Blueprint("device", __name__)


@device_bp.route("/scan", methods=["GET"])
def scan():
    devices = get_adb_port()
    return jsonify([d.to_dict() for d in devices])


@device_bp.route("/connect", methods=["POST"])
def connect_device():
    data = request.get_json() or {}
    port = data.get("port")
    if not port:
        return jsonify({"success": False, "error": "缺少 port 参数"}), 400
    ok = connect(port)
    dev = get_device()
    actual_method = "nemu" if isinstance(dev, NEMU) else "adb" if isinstance(dev, ADB) else dev.__class__.__name__
    requested_touch = getattr(app.Global.touch_method, "value", app.Global.touch_method)
    requested_screenshot = getattr(app.Global.screenshot_method, "value", app.Global.screenshot_method)
    requested_nemu = requested_touch == "nemu" or requested_screenshot == "nemu"
    return jsonify({
        "success": ok,
        "actual_method": actual_method,
        "requested_touch_method": requested_touch,
        "requested_screenshot_method": requested_screenshot,
        "fallback": bool(ok and requested_nemu and actual_method != "nemu"),
    })


@device_bp.route("/status", methods=["GET"])
def device_status():
    dev = get_device()
    actual_method = "nemu" if isinstance(dev, NEMU) else "adb" if isinstance(dev, ADB) else None
    return jsonify({"connected": dev is not None, "actual_method": actual_method})


@device_bp.route("/restart-game", methods=["POST"])
def restart_game_route():
    try:
        ok = restart_game()
        return jsonify({"success": ok})
    except Exception as e:
        logger.exception("重启游戏失败")
        return jsonify({"success": False, "error": str(e)}), 500


@device_bp.route("/start-game", methods=["POST"])
def start_game_route():
    try:
        result = start_game()
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        logger.exception("启动游戏失败")
        return jsonify({"success": False, "error": str(e)}), 500


@device_bp.route("/stop-game", methods=["POST"])
def stop_game_route():
    try:
        result = stop_game()
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        logger.exception("关闭游戏失败")
        return jsonify({"success": False, "error": str(e)}), 500


@device_bp.route("/benchmark-screenshot", methods=["POST"])
def benchmark_screenshot_route():
    data = request.get_json() or {}
    try:
        result = benchmark_screenshot_methods(
            port=data.get("port"),
            samples=int(data.get("samples", 5)),
            warmup=int(data.get("warmup", 1)),
            apply_fastest=bool(data.get("apply_fastest", False)),
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("截图测速失败")
        return jsonify({"success": False, "error": str(e)}), 500


@device_bp.route("/debug-ocr", methods=["POST"])
def debug_ocr():
    try:
        from resonance.server.routes.debug import debug_snapshot

        return debug_snapshot()
    except Exception as e:
        logger.exception("截图并OCR失败")
        return jsonify({"success": False, "error": str(e)}), 500
