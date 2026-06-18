"""Flask 应用：创建后端 HTTP + WebSocket 服务。

  注册所有蓝图（device / config / scheduler / business / status / debug）。
  原生 WebSocket 端点 /ws（flask-sock）。
  SECRET_KEY 从环境变量 SECRET_KEY 读取，默认 fallback 用于 dev。
  启用 CORS，允许通配符 origin。
"""

import os

from flask import Flask
from flask_cors import CORS
from flask_sock import Sock

from resonance.server.routes import register_blueprints

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
CORS(app)
sock = Sock(app)


def create_app():
    register_blueprints(app)
    return app
