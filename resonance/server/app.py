"""Flask 应用：创建后端 HTTP + WebSocket 服务。

   注册所有蓝图（device / config / scheduler / business / status / debug）。
   原生 WebSocket 端点 /ws（flask-sock）。
   SECRET_KEY 从环境变量 SECRET_KEY 读取，默认 fallback 用于 dev。
   启用 CORS，允许通配符 origin。
   若 web/dist/ 存在，托管前端静态文件（SPA fallback）。
"""

import os
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sock import Sock

from resonance.server.routes import register_blueprints
from resonance.utils.utils import ROOT_PATH

app = Flask(__name__, static_folder=None)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
CORS(app)
sock = Sock(app)

_frontend_dist = ROOT_PATH / "web" / "dist"


def _register_frontend():
    dist = _frontend_dist.resolve()
    if not dist.is_dir() or not (dist / "index.html").is_file():
        return

    @app.route("/")
    def serve_index():
        return send_from_directory(str(dist), "index.html")

    @app.route("/<path:filename>")
    def serve_frontend(filename: str):
        target = dist / filename
        if target.is_file():
            return send_from_directory(str(dist), filename)
        return send_from_directory(str(dist), "index.html")


def create_app():
    register_blueprints(app)
    _register_frontend()
    return app
