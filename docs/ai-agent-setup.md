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
