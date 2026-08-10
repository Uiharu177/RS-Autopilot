# AI Agent 安装提示词

将以下内容贴给 AI 助手即可快速安装和启动本项目。

---

```
帮我安装并启动 RS-Autopilot，一个《雷索纳斯》手游的自动化工具。

## 项目概览
- 后端：Python 3.11/3.12 / Flask / loguru / pydantic
- 前端：Vue 3 + TypeScript + Naive UI
- 设备控制：ADB / MuMu IPC / DroidCast / Scrcpy
- 视觉：ONNX PaddleOCR / OpenCV 模板匹配
- 详细架构见 docs/architecture.md

## 买卖模块约束

- `purchase.py` 是实际买货实现，负责商品选择、议价、买入确认和买入结算页关闭。
- `sale.py` 是实际卖货实现，负责空车保护、议价、卖出确认和卖出结算页关闭。
- `exchange.py` 只负责交易所页面定位、进入、页签切换和离开。
- `buy.py` 与 `sell.py` 仅保留旧导入路径的兼容转发，不得恢复业务实现。
- 买入、卖出按钮均只允许一次确认点击；不能用单像素颜色作为成功的唯一依据。
- 买卖结算页必须在 `purchase.py` / `sale.py` 内确认并关闭；修改前先阅读 `docs/single-trade-flow.md`。
- 内部模块重构不得改变 REST API、WebSocket 消息、前端协议、配置字段或批处理入口。

## 安装步骤

1. 安装 Python 依赖：
   pip install -r requirements.txt

2. 安装前端依赖并构建：
   cd web
   npm install
   npm run build
   cd ..

3. 一键启动（也可直接运行 start.bat）：
   后端：python cli.py serve
   前端由后端托管，访问 http://localhost:15177
```
