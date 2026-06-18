from flask import Blueprint, jsonify, request

from resonance.model.config import config
from resonance.model.runtime import app
from resonance.model.runtime import ScreenshotMethod, TouchMethod

config_bp = Blueprint("config", __name__)


@config_bp.route("/get", methods=["GET"])
def get_config():
    return jsonify({
        "config": config.model_dump(mode="json"),
        "app": app.model_dump(mode="json"),
    })


@config_bp.route("/save", methods=["POST"])
def save_config():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "缺少配置数据"}), 400

    # Update global_config fields
    if "global_config" in data:
        gc = data["global_config"]
        for key, value in gc.items():
            if hasattr(config.global_config, key):
                setattr(config.global_config, key, value)

    # Update app.Global fields (device settings)
    if "port" in data:
        app.Global.device.port = data["port"]
    if "device_path" in data:
        app.Global.device.path = data["device_path"]
    if "device_type" in data:
        from resonance.device.port_scanner import EmulatorType
        app.Global.device.type = EmulatorType(data["device_type"])
    if "device_index" in data:
        app.Global.device.index = data["device_index"]
    for key in ("touch_method", "screenshot_method"):
        if key in data:
            if key == "touch_method":
                app.Global.touch_method = TouchMethod(data[key])
            else:
                app.Global.screenshot_method = ScreenshotMethod(data[key])

    # Update app (runtime) fields
    for key in ("CityBook", "CityHaggle"):
        if key in data:
            setattr(app, key, data[key])
    if "RunBuy" in data:
        app.RunBuy = app.RunBuy.__class__.model_validate({
            **app.RunBuy.model_dump(mode="json"),
            **data["RunBuy"],
        })

    config.save_config()
    app.save_config()
    return jsonify({"success": True})


@config_bp.route("/city-config", methods=["GET"])
def get_city_config():
    return jsonify({
        "CityBook": app.CityBook,
        "CityHaggle": app.CityHaggle,
        "RunBuy": app.RunBuy.model_dump(mode="json"),
    })


@config_bp.route("/city-config", methods=["POST"])
def save_city_config():
    data = request.get_json() or {}
    if "CityBook" in data:
        app.CityBook.update(data["CityBook"])
    if "CityHaggle" in data:
        app.CityHaggle.update(data["CityHaggle"])
    if "RunBuy" in data:
        run_buy = data["RunBuy"]
        app.RunBuy.BuyCount = run_buy.get("BuyCount", app.RunBuy.BuyCount)
        app.RunBuy.BuyCity = run_buy.get("BuyCity", app.RunBuy.BuyCity)
        app.RunBuy.SellCity = run_buy.get("SellCity", app.RunBuy.SellCity)
        if "LoopCities" in run_buy:
            app.RunBuy.LoopCities = run_buy["LoopCities"]
    config.save_config()
    app.save_config()
    return jsonify({"success": True})
