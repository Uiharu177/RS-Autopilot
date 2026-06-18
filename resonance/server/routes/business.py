import time

from flask import Blueprint, jsonify, request

from resonance.model.runtime import CITYS, app
from resonance.scheduler import scheduler
from resonance.scheduler.models import Task, TaskType
from resonance.device.device import stop as stop_device_actions

business_bp = Blueprint("business", __name__)


@business_bp.route("/cities", methods=["GET"])
def list_cities():
    return jsonify(CITYS)


@business_bp.route("/start", methods=["POST"])
def start_business():
    data = request.get_json() or {}
    cities = data.get("cities")
    buy_city = data.get("buy_city", "")
    sell_city = data.get("sell_city", "")

    if cities and len(cities) >= 2:
        pass  # use cities list
    elif buy_city and sell_city:
        cities = [buy_city, sell_city]
    else:
        return jsonify({"success": False, "error": "请提供城市列表（cities）或买卖城市（buy_city + sell_city）"}), 400

    stop_device_actions()
    scheduler.unregister("resonance.solvers.trade.TradeRouteSolver")
    time.sleep(0.5)

    app.RunBuy.BuyCity = cities[0]
    app.RunBuy.SellCity = cities[-1]
    app.RunBuy.LoopCities = cities
    app.save_config()

    from resonance.solvers.trade import TradeRouteSolver

    route_str = "→".join(cities)
    solver = TradeRouteSolver(cities=cities)
    task = Task(
        name=f"跑商 {route_str}",
        solver_path="resonance.solvers.trade.TradeRouteSolver",
        priority=1,
        task_type=TaskType.ONETIME,
        kwargs={"cities": cities},
    )
    if not scheduler.is_running:
        scheduler.start()
    scheduler.register(task)
    return jsonify({"success": True})


@business_bp.route("/stop", methods=["POST"])
def stop_business():
    stop_device_actions()
    scheduler.unregister("resonance.solvers.trade.TradeRouteSolver")
    scheduler.stop()
    return jsonify({"success": True})
