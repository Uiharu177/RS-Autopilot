from flask import Blueprint, jsonify

from resonance.scheduler import scheduler

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/start", methods=["POST"])
def start_scheduler():
    scheduler.start()
    return jsonify({"success": True, "running": scheduler.is_running})


@scheduler_bp.route("/stop", methods=["POST"])
def stop_scheduler():
    scheduler.stop()
    return jsonify({"success": True, "running": scheduler.is_running})


@scheduler_bp.route("/status", methods=["GET"])
def scheduler_status():
    return jsonify({
        "running": scheduler.is_running,
        "task_count": len(scheduler.tasks),
    })
