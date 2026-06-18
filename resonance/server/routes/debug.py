from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from loguru import logger

from resonance.debug.snapshot import DEBUG_DIR, capture_debug_snapshot
from resonance.utils.screenshot_logger import SCREENSHOT_DIR
from resonance.model.runtime import CITYS, app
from resonance.utils.exceptions import StopExecution

debug_bp = Blueprint("debug", __name__)

LOG_DIR = Path("logs")


def _safe_log_path(filename: str) -> Path:
    path = (LOG_DIR / filename).resolve()
    root = LOG_DIR.resolve()
    if root not in path.parents and path != root:
        raise ValueError("非法日志路径")
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path


@debug_bp.route("/snapshot", methods=["POST"])
def debug_snapshot():
    """Capture a mower-ng style debug snapshot: screenshot + OCR + scene + matches."""
    data = request.get_json() or {}
    templates = data.get("templates") or []
    if not isinstance(templates, list):
        return jsonify({"success": False, "error": "templates 必须是列表"}), 400

    try:
        return jsonify(capture_debug_snapshot(templates=templates, reason=data.get("reason")))
    except StopExecution:
        return jsonify({"success": False, "stopped": True, "error": "停止执行程序"}), 409
    except Exception as e:
        logger.exception("调试快照失败")
        return jsonify({"success": False, "error": str(e)}), 500


@debug_bp.route("/trade-page-flow", methods=["POST"])
def trade_page_flow():
    """Run trade-route page flow without clicking 'go station' or monitoring travel."""
    data = request.get_json() or {}
    cities = data.get("cities")
    buy_city = data.get("buy_city") or app.RunBuy.BuyCity
    sell_city = data.get("sell_city") or app.RunBuy.SellCity

    if cities and len(cities) >= 2:
        pass
    elif buy_city and sell_city:
        cities = [buy_city, sell_city]
    else:
        return jsonify({"success": False, "error": "请提供城市列表（cities）或买卖城市（buy_city + sell_city）"}), 400

    for c in cities:
        if c not in CITYS:
            return jsonify({"success": False, "error": f"城市名称无效: {c}"}), 400

    try:
        rounds = int(data.get("rounds") or 1)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "rounds 必须是整数"}), 400
    rounds = max(1, min(rounds, 20))

    try:
        from resonance.solvers.trade import TradeRouteSolver

        app.RunBuy.BuyCity = cities[0]
        app.RunBuy.SellCity = cities[-1]
        app.RunBuy.LoopCities = cities
        app.save_config()

        solver = TradeRouteSolver(cities=cities)
        ok = solver.run_page_flow(rounds=rounds)
        return jsonify({
            "success": ok,
            "cities": cities,
            "rounds": rounds,
        })
    except StopExecution:
        return jsonify({"success": False, "stopped": True, "error": "停止执行程序"}), 409
    except Exception as e:
        logger.exception("跑商页面流程失败")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@debug_bp.route("/logs", methods=["GET"])
def list_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(LOG_DIR.glob("runtime*log"), key=lambda p: p.name, reverse=True)
    # runtime.log 置顶（不带后缀的当前活跃文件）
    main = [f for f in files if f.name == "runtime.log"]
    files = main + [f for f in files if f.name != "runtime.log"]
    logs = []
    for path in files:
        stat = path.stat()
        logs.append({
            "name": path.name,
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
        })
    return jsonify({"success": True, "logs": logs})


@debug_bp.route("/logs/recent", methods=["GET"])
def recent_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines_count = int(request.args.get("lines", 200))
    lines_count = max(1, min(lines_count, 5000))
    level = request.args.get("level", "").upper()
    search = request.args.get("search", "")

    candidates = list(LOG_DIR.glob("runtime*.log"))
    for p in LOG_DIR.glob("runtime_*.log"):
        if p.name not in [c.name for c in candidates]:
            candidates.append(p)
    if not candidates:
        return jsonify({"success": True, "name": None, "lines": [], "total": 0})

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()

    if level:
        lines = [l for l in lines if f" {level} " in l]
    if search:
        lines = [l for l in lines if search.lower() in l.lower()]

    return jsonify({
        "success": True,
        "name": latest.name,
        "lines": lines[-lines_count:],
        "total": len(lines),
    })


@debug_bp.route("/logs/<path:filename>", methods=["GET"])
def read_log(filename: str):
    try:
        limit = int(request.args.get("limit", 500))
        limit = max(1, min(limit, 5000))
        level = request.args.get("level", "").upper()
        search = request.args.get("search", "")

        is_rotated = filename.count(".") >= 2 and len(filename.rsplit(".", 1)[0].rsplit("_", 1)) > 1

        if is_rotated:
            path = _safe_log_path(filename)
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        else:
            base = filename.rsplit(".", 1)[0] if filename.count(".") >= 2 else filename.rsplit(".", 1)[0]
            _safe_log_path(Path(base).with_suffix(".log").name)
            all_lines: list[str] = []
            for p in sorted(LOG_DIR.glob(f"{base}.*.log")):
                all_lines.extend(p.read_text(encoding="utf-8", errors="replace").splitlines())
            main = LOG_DIR / filename
            if main.is_file():
                _safe_log_path(filename)
                all_lines.extend(main.read_text(encoding="utf-8", errors="replace").splitlines())
            if not all_lines:
                raise FileNotFoundError(filename)
            all_lines.sort(key=lambda line: line[:8] if len(line) >= 8 and line[2] == ":" else "")
            lines = all_lines

        if level:
            lines = [l for l in lines if f" {level} " in l]
        if search:
            lines = [l for l in lines if search.lower() in l.lower()]

        return jsonify({
            "success": True,
            "name": filename,
            "lines": lines[-limit:],
            "total": len(lines),
        })
    except Exception as e:
        logger.exception("读取调试日志失败")
        return jsonify({"success": False, "error": str(e)}), 404


@debug_bp.route("/screenshot/<path:filename>", methods=["GET"])
def serve_screenshot(filename):
    try:
        path = (SCREENSHOT_DIR / filename).resolve()
        root = SCREENSHOT_DIR.resolve()
        if root not in path.parents and path != root:
            raise ValueError("非法截图路径")
        if not path.is_file():
            raise FileNotFoundError(filename)
        return send_file(path)
    except Exception as e:
        logger.exception("读取截图失败")
        return jsonify({"success": False, "error": str(e)}), 404


SC_MARKER = "[SC]"


@debug_bp.route("/screenshots", methods=["GET"])
def list_screenshots():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted(SCREENSHOT_DIR.glob("*.jpg"), reverse=True):
        stat = p.stat()
        files.append({
            "name": p.name,
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "ts_ns": int(p.stem),
        })
    return jsonify({"success": True, "screenshots": files})


@debug_bp.route("/timeline/<path:filename>", methods=["GET"])
def timeline(filename):
    try:
        is_rotated = filename.count(".") >= 2 and len(filename.rsplit(".", 1)[0].rsplit("_", 1)) > 1

        if is_rotated:
            path = _safe_log_path(filename)
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        else:
            base = filename.rsplit(".", 1)[0] if filename.count(".") >= 2 else filename.rsplit(".", 1)[0]
            _safe_log_path(Path(base).with_suffix(".log").name)
            all_lines: list[str] = []
            for p in sorted(LOG_DIR.glob(f"{base}.*.log")):
                all_lines.extend(p.read_text(encoding="utf-8", errors="replace").splitlines())
            main = LOG_DIR / filename
            if main.is_file():
                _safe_log_path(filename)
                all_lines.extend(main.read_text(encoding="utf-8", errors="replace").splitlines())
            if not all_lines:
                raise FileNotFoundError(filename)
            all_lines.sort(key=lambda line: line[:8] if len(line) >= 8 and line[2] == ":" else "")
            lines = all_lines

        segments = []
        current = {"time": "", "log_lines": [], "screenshot": None}

        for line in lines:
            if SC_MARKER in line:
                sc_name = line.split(SC_MARKER)[-1].strip()
                if current["log_lines"]:
                    segments.append(current)
                    current = {"time": line[:14], "log_lines": [], "screenshot": sc_name}
                elif segments:
                    segments[-1]["screenshot"] = sc_name
                    current = {"time": line[:14], "log_lines": [], "screenshot": None}
                else:
                    current = {"time": line[:14], "log_lines": [], "screenshot": sc_name}
            else:
                if not current["time"]:
                    current["time"] = line[:14]
                current["log_lines"].append(line)

        if current["log_lines"]:
            if current["screenshot"] and segments and not segments[-1]["screenshot"]:
                segments[-1]["screenshot"] = current["screenshot"]
            segments.append(current)
        elif current["screenshot"] and segments:
            segments[-1]["screenshot"] = current["screenshot"]

        return jsonify({"success": True, "name": filename, "segments": segments, "total": len(segments)})
    except Exception as e:
        logger.exception("读取时间轴失败")
        return jsonify({"success": False, "error": str(e)}), 404


@debug_bp.route("/files/<path:filename>", methods=["GET"])
def get_debug_file(filename: str):
    try:
        path = (DEBUG_DIR / filename).resolve()
        root = DEBUG_DIR.resolve()
        if root not in path.parents and path != root:
            raise ValueError("非法调试文件路径")
        if not path.is_file():
            raise FileNotFoundError(filename)
        return send_file(path)
    except Exception as e:
        logger.exception("读取调试文件失败")
        return jsonify({"success": False, "error": str(e)}), 404
