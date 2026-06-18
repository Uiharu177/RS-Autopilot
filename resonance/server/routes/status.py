from flask import Blueprint, jsonify
from loguru import logger

from resonance.device.device import connect
from resonance.scene.recognizer import Recognizer
from resonance.scheduler import scheduler
from resonance.utils.exceptions import StopExecution

status_bp = Blueprint("status", __name__)


@status_bp.route("/scene", methods=["GET"])
def current_scene():
    if not scheduler.is_running:
        return jsonify({"success": True, "scene": None, "value": None, "text": [], "ocr": [], "idle": True})

    try:
        recog = Recognizer()
        recog.update()
        try:
            scene = recog.scene
        except StopExecution:
            return jsonify({"success": False, "stopped": True, "error": "停止执行程序"}), 409
        except Exception as e:
            logger.debug(f"状态场景截图失败，尝试重新连接设备: {e}")
            if not connect(reset_stop=False):
                return jsonify({"success": False, "error": "设备未连接，且自动连接失败"}), 500
            recog.update()
            scene = recog.scene
        ocr_results = recog.ocr()
        return jsonify({
            "success": True,
            "scene": scene.name if scene else None,
            "value": int(scene) if scene else None,
            "text": [r["text"] for r in ocr_results],
            "ocr": ocr_results,
        })
    except StopExecution:
        return jsonify({"success": False, "stopped": True, "error": "停止执行程序"}), 409
    except Exception as e:
        logger.exception("读取当前场景失败")
        return jsonify({"success": False, "error": str(e)}), 500
