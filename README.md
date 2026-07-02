# RS-Autopilot — RS自动驾驶

**RS-Autopilot**（RS自动驾驶）是《雷索纳斯》(Resonance Solstice) 手游的自动化工具，支持自动跑商相关的核心玩法。技术栈：Python / Flask / ADB / MuMu IPC / DroidCast / Scrcpy / OCR / Vue 3

> ⚠️ **免责声明**
>
> 1. 本项目仅用于**学习和研究**目的，严禁用于商业用途或破坏游戏公平性的行为。
> 2. 使用本项目产生的任何后果（包括但不限于账号封禁、数据丢失等）由使用者自行承担，项目开发者不承担任何责任。
> 3. 本项目与《雷索纳斯》官方无任何关联，未取得任何官方授权。
> 4. 使用前请仔细阅读游戏用户协议，确认是否允许第三方自动化工具。
> 5. 如游戏官方要求停止，本项目将立即下架并删除所有相关内容。
> 6. 本项目**由 AI 生成**，代码质量不保证，使用前请自行审查代码。
> 7. **beta 阶段** — API 和配置格式可能随时变化，不保证向后兼容。
> 8. 本人无力维护，请自行解决遇到的问题。
>
> 继续使用即代表你同意以上条款。

参考项目：[Auto_Resonance](https://github.com/Night-stars-1/Auto_Resonance) · [mower-ng](https://git.zhaozuohong.vip/mower-ng)

---

## 主要功能

### 自动跑商
- **端点模式** — A ↔ B 往返跑商，支持配置交易次数、买入/卖出城市（支持武林源）
- **环线模式** — 多城市循环跑商，自动归位至首城
- **自动议价** — 根据城市议价等级自动议价
- **体力管理** — 自动使用体力道具，脚本停止后可选择停在原地、返回主界面或关闭游戏

### 自动导航
- 自动规划路线，游戏地图内自动滑动定位站点
- OCR + 模板匹配识别当前场景和站点
- 断线重连 / 弹窗处理 / 崩溃恢复，自动回到跑商流程

### 设备控制
- **ADB** — 通用方式，通过 TCP 控制模拟器
- **MuMu IPC** — MuMu 12 原生 IPC 协议，截图延迟更低（~6ms vs ADB ~600ms）
- **DroidCast** — HTTP 截图，触控委托 ADB
- **Scrcpy** — H.264 视频流截图 + 控制通道触控（需 `pip install av`）
- **多模拟器** — 支持 MuMu 12 及通用 ADB 设备
- **截图/触控方式** — 独立可选，失败自动降级 ADB

### 任务调度
- 后台自动执行跑商循环，支持启停控制
- WebSocket 实时推送日志和截图至前端

### Web 控制台

| 页面 | 路由 | 说明 |
|------|------|------|
| 控制中心 | `/` | 状态面板、实时日志、截图预览、任务启停 |
| 路线编排 | `/business` | 端点/环线跑商配置 |
| 设备配置 | `/device` | 模拟器扫描、连接、测速、游戏启停 |
| 系统设置 | `/settings` | 体力药、停止条件、停止后动作等自动化偏好 |
| 开发调试 | `/debug` | 日志回放、截图时间线 |
| 关于 | `/about` | 项目说明与免责声明 |

### 已知问题
1. 日志输出不够清晰
2. UI 比较简陋（尽力了）
3. AI 生成的代码可能产生各种莫名其妙的 Bug

---

## 环境要求

- **OS**: Windows 10/11
- **Python**: 3.11 或 3.12 — [下载](https://www.python.org/downloads/)
- **Node.js**: 18+ — [下载](https://nodejs.org/)
- **模拟器**: [MuMu 模拟器 12](https://mumu.163.com/mumu12/)

## 快速开始

> 遇到问题时，如有必要可寻求 AI 帮助，把报错信息和当前操作贴给 AI 通常能快速定位问题。可将 docs/ai-agent-setup.md 喂给 agent 帮你安装。

### 1. 克隆项目

> 执行路径：你希望存放的位置

```
git clone https://github.com/Uiharu177/RS-Autopilot.git
cd RS-Autopilot
```

### 2. 安装 Python
下载并安装 Python 3.11 或 3.12，安装时勾选 "Add Python to PATH"。

> 执行路径：任意

验证安装：
```
python --version
```

### 3. 安装 Node.js
下载并安装 Node.js 18 或更高版本（用于首次构建前端，运行时不需要）。

> 执行路径：任意

验证安装：
```
node --version
```

### 4. 安装 Python 依赖

> 执行路径：项目根目录

升级 pip（可选）：
```
python -m pip install --upgrade pip
```

安装项目依赖：
```
pip install -r requirements.txt
```

### 5. 启动

> 执行路径：项目根目录

```
start.bat
```
`start.bat` 会自动完成：
1. 安装前端依赖（`npm install`）
2. 构建前端到 `web/dist/`（`npm run build`）
3. 启动后端服务，端口 15177，前端由后端托管
4. 自动打开浏览器 http://127.0.0.1:15177/#/

> 备选：仅启动后端 API（不含前端界面）

> 执行路径：项目根目录

```
python cli.py serve
```

### 6. 配置模拟器
浏览器打开后进入「设备配置」→「扫描」→ 选中模拟器 →「使用此设备」
或启动前手动复制 `config/app.example.json` 为 `config/app.json` 填写设备信息。

## 端口被占用？

项目默认使用端口 `15177`，若该端口被其他程序占用，可修改以下两处改为空闲端口：

> 后端端口（`cli.py` 第 `app.run(...)` 一行）

```
app.run(host="127.0.0.1", port=15177, debug=False, use_reloader=False)
```

> 前端 API/WebSocket 地址（`web/src/api/index.ts` 前两行）

```
export const API_ORIGIN = 'http://127.0.0.1:15177'
export const WS_ORIGIN = 'ws://127.0.0.1:15177'
```

修改后需重新执行 `npm run build`（在 `web/` 目录）再 `start.bat` 生效。

## 更新

> 执行路径：项目根目录

拉取最新代码：
```
git pull
```

更新 Python 依赖：
```
pip install -r requirements.txt
```

安装前端依赖并重新构建：
```
cd web
npm install
npm run build
cd ..
```
> 重新执行 `start.bat` 即可重新启动。

## 项目结构

| 路径 | 说明 |
|------|------|
| `cli.py` | CLI 入口 |
| `resonance/` | Python 后端 |
| `  device/` | ADB / MuMu IPC 设备控制 |
| `  vision/` | OCR 识别、模板匹配 |
| `  scene/` | 场景识别系统 |
| `  solvers/` | 业务逻辑（跑商、导航、恢复） |
| `  scheduler/` | 后台任务调度 |
| `  server/` | Flask API + WebSocket |
| `web/` | Vue 3 前端（RS自动驾驶控制台） |
| `resources/` | 游戏数据、图片模板 |
| `config/` | 运行时配置 |
| `docs/` | 文档目录 |
| `docs/architecture.md` | 系统架构与操作逻辑说明 |
| `docs/add-station-guide.md` | 新增站点完整教程（坐标标定、商品/疲劳数据填写） |

## 卸载

### 1. 停止服务

> 执行路径：项目根目录

```
stop.bat
```
或关闭所有 RS-Autopilot 命令行窗口。

### 2. 卸载 Python 依赖（可选）

> 执行路径：任意

```
pip uninstall -y Pillow loguru numpy opencv-python orjson pydantic watchdog adb-shell onnxocr-ppocrv4 requests psutil onnxruntime flask flask-cors flask-sock simple-websocket networkx pyyaml
```

> 如安装时额外装了 scrcpy 可选依赖，可一并卸载：

> 执行路径：任意

```
pip uninstall -y av
```

### 3. 删除项目目录
直接删除整个 RS-Autopilot 文件夹即可，所有配置和日志都在该目录内。

> 可能导致的后果：已保存的跑商路线/城市配置、运行日志、调试截图都会丢失；如需保留请先备份 `config/` 和 `logs/` 目录。

> MuMu 模拟器与游戏本身不受影响，如需卸载请另行处理。

## License

MIT
