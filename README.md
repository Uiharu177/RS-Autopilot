# RS-Autopilot — RS自动驾驶

**RS-Autopilot**（RS自动驾驶）是《雷索纳斯》(Resonance Solstice) 手游的自动化工具，支持自动跑商相关的核心玩法。技术栈：Python + Flask + ADB/MuMu IPC + OCR + Vue 3

> ⚠️ **免责声明**
>
> 1. 本项目仅用于**学习和研究**目的，严禁用于商业用途或破坏游戏公平性的行为。
> 2. 使用本项目产生的任何后果（包括但不限于账号封禁、数据丢失等）由使用者自行承担，项目开发者不承担任何责任。
> 3. 本项目与《雷索纳斯》官方及网易无任何关联，未取得任何官方授权。
> 4. 使用前请仔细阅读游戏用户协议，确认是否允许第三方自动化工具。
> 5. 如游戏官方要求停止，本项目将立即下架并删除所有相关内容。
> 6. 本项目**由 AI 生成**，代码质量不保证，使用前请自行审查代码。
> 7. **beta 阶段** — API 和配置格式可能随时变化，不保证向后兼容。
> 8. 本人无力维护，请自行解决遇到的问题。
>
> 继续使用即代表你同意以上条款。

参考项目：[Auto_Resonance](https://github.com/Night-stars-1/Auto_Resonance)

---

## 主要功能

### 自动跑商
- **端点模式** — A ↔ B 往返跑商，支持配置交易次数、买入/卖出城市（支持武林源）
- **环线模式** — 多城市循环跑商，自动归位至首城
- **自动议价** — 根据城市议价等级自动议价
- **体力管理** — 自动使用体力道具，体力耗尽时退出或关闭游戏

### 智能导航
- 自动规划路线，游戏地图内自动滑动定位站点
- OCR + 模板匹配识别当前场景和站点
- 断线重连 / 弹窗处理 / 崩溃恢复，自动回到跑商流程

### 设备控制
- **ADB** — 通用方式，通过 TCP 控制模拟器
- **MuMu IPC** — MuMu 12 原生 IPC 协议，截图延迟更低（~6ms vs ADB ~600ms）
- **多模拟器** — 支持 MuMu 12 及通用 ADB 设备
- **截图方式** — 可选 ADB / NEMU IPC / Scrcpy / DroidCast

### 任务调度
- 后台自动执行跑商循环，支持启停控制
- WebSocket 实时推送日志和截图至前端

### Web 控制台

| 页面 | 路由 | 说明 |
|------|------|------|
| 控制中心 | `/` | 状态面板、实时日志、截图预览、任务启停 |
| 路线编排 | `/business` | 端点/环线跑商配置 |
| 设备配置 | `/device` | 模拟器扫描、连接、测速、游戏启停 |
| 系统设置 | `/settings` | 体力药、疲劳保护等自动化偏好 |
| 开发调试 | `/debug` | 日志回放、截图时间线 |
| 关于 | `/about` | 项目说明与免责声明 |

### 已知问题
1. 日志输出不够清晰
2. UI 比较简陋（尽力了）
3. AI 生成的代码可能产生各种莫名其妙的 Bug

---

## 环境要求

- **OS**: Windows 10/11
- **Python**: 3.11 或 3.12
- **Node.js**: 18+（前端需要）
- **模拟器**: [MuMu 模拟器 12](https://mumu.163.com/mumu12/)

## 快速开始

```
# 1. 安装 Python 依赖
pip install -e .

# 2. 配置模拟器
#    打开「设备配置」页面 → 点击「扫描」→ 在列表中找到模拟器，点击「使用此设备」
#    或手动复制 config/app.example.json 为 config/app.json 填写设备信息

# 3. 启动
start.bat                    # 一键启动后端(:5000) + 前端(:5173)
resonance serve              # 或仅启动后端 API
```

> **注意**
> - `pip install -e .` 必须在项目根目录执行，装完后 `resonance` 命令全局可用
> - `start.bat` 不需要先 `pip install`，它直接用 `python cli.py serve` 启动
> - `start.bat` 会自动执行 `npm install` 安装前端依赖（如果还没装过）
> - `resonance serve` 只启动后端 API（端口 5000），不含前端界面
> - 模拟器配置也可以通过浏览器操作：`start.bat` 启动后打开 `http://127.0.0.1:5173`，进入「设备配置」页面配置

## CLI 命令

```
resonance scan                   # 扫描模拟器
resonance connect --port 16384   # 测试 ADB 连接
resonance screenshot             # 测试截图
resonance start-game             # 启动游戏
resonance stop-game              # 关闭游戏
resonance serve                  # 启动 Web 控制台
```

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
| `docs/` | 架构文档 |

## License

MIT
