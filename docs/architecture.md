# RS-Autopilot 架构与操作逻辑

## 技术栈

Python 3.11/3.12 / Flask + simple-websocket / Vue 3 + Naive UI
ONNX PaddleOCR / OpenCV / ADB / MuMu IPC / DroidCast / Scrcpy

## 分层架构

```
前端 (Vue 3)
  ↓ REST / WebSocket
Flask API + WebSocket 推送
  ↓
Scheduler 调度器 → 任务生命周期
  ↓
Solvers 业务流程 → boot / trade / recovery
  ↓
Preset + Navigation → 通用交互
  ↓
Scene Recognizer → 场景识别
  ↓
Vision → OCR / Template / Image
  ↓
  Device → ADB / NEMU / DroidCast / Scrcpy
```

### 各层职责

| 层 | 职责 |
|---|------|
| Device | 统一接口：截图、点击、启动/关闭游戏。支持 4 种截图方式（ADB/NEMU/DroidCast/Scrcpy）和 3 种触控方式（ADB/NEMU/Scrcpy），失败自动降级 ADB。NEMU 连接分段化——`connect()` 只拿 IPC 连接，display_id 首次截图时懒加载 |
| Vision | ONNX OCR 裁剪/缓存、模板匹配、BGR/HSV 颜色判断 |
| Scene | 级联 detector 识别当前页面，场景转移图引导恢复 |
| Solvers | boot (万能启动)、trade (环线/端点跑商编排)、navigation (地图导航/行车监听)、recovery (接管/纠错) |
| Scheduler | 线程内任务执行 + STOP 标志位控制 |
| Server | REST API + WebSocket 日志/截图推送 |

## 设备连接策略

### 截图/触控方式

| 方式 | 截图 | 触控 | 原理 | 要求 |
|------|------|------|------|------|
| ADB | screencap | input tap/swipe | ADB 守护进程 | 无额外依赖 |
| NEMU | MuMu IPC | MuMu IPC | nemu_dll.dll | MuMu 12 模拟器 |
| DroidCast | HTTP Java 服务 | 委托 ADB | APK 安装到模拟器 | DroidCast APK（未测试） |
| Scrcpy | H.264 视频流 | 控制通道 | scrcpy-server.jar + PyAV | scrcpy jar + `pip install av`（未测试） |

`connect()` 按优先级选设备：**Scrcpy > NEMU > DroidCast > ADB**，连接失败自动降级到 ADB。

### NEMU 懒加载

截图/触控方式选 NEMU 时：
1. `connect()` → `nemu_connect` 获取 IPC 连接，成功即返回
2. `check_status()` 只检查 `connect_id > 0`，不要求 display_id
3. 首次 `screenshot()` / `input_tap()` → `_ensure_display()` → `_acquire_display()` 获取 display_id + 分辨率
4. 游戏未运行 → display_id < 0 → `ConnectionError` → 上级 catch 后降级到 ADB
5. 游戏启动后 → 下次操作自动拿到 display_id → 切回 NEMU IPC

### STOP 守卫

`stop()` 设 `STOP = True`（不杀游戏）。此后：
- `_ensure_connected()` 检测 `STOP` 直接返回，不重连、不清标志
- `screenshot()` / `screenshot_image()` 检测 `STOP` 抛出 `StopExecution`
- `NEMU.connect()` 不再内部 auto-start 游戏（启动权在 `boot_game()`）
- `kill()` 独立调用 → `am force-stop` 关闭游戏进程（与 STOP 无关）

## 启动流程（boot_game)

```
launch_emulator()       → 启动模拟器
connect(port)           → NEMU IPC 连接（不要求游戏渲染）
is_game_foreground()?   → 否
start_game()            → ADB monkey 启动游戏
recover_to_expected()   → 等加载、关弹窗、到站接管
  → 首次截图自动获取 display_id → 切 NEMU IPC
  → 城市识别 → 返回 city_name
```

## 跑商编排（TradeRouteSolver）

### 端点模式

```
for _ in range(BuyCount):
    buy_city 买 → travel → sell_city 卖
```

### 环线模式

```
cities = [A, B, C, D]
A→B(买→卖) → B→C(买→卖) → C→D(买→卖) → D→A(买→卖)
```

- 环线首城先 `_sell_current_goods(0)` 清空车厢
- 归位段不计轮次
- `BuyCount = 0` 不运行

### 体力检查

每城一次（卖货后买货前），通过 `use_stamina_item` 与 `fatigue_action` 两个开关控制：

```
体力检查通过？→ 继续
体力不足：
  use_stamina_item? → 尝试使用道具 → 成功继续 / 失败走下一步
  fatigue_action != "none"? → STOP = True（停止脚本，不杀游戏），记下 fatigue_action 供 finally 执行
  fatigue_action == "none" → warning 继续（影响议价）
```

### 停止与后置动作

脚本内部的停止逻辑 **只设 STOP 标志或 return**，不再内联 kill 游戏进程。停止后执行什么由 `fatigue_action` 与 `on_stop_action` 两个配置决定，二者取值相同（`fatigue_action` 额外允许 `none`）：

| 值 | 行为 | 说明 |
|----|------|------|
| `stay_there` | 停在原地 | 脚本停止，游戏保持当前界面（`on_stop_action` 默认值） |
| `goto_main` | 返回主界面 | 调用 `safe_go_home()` 回到大地图 |
| `close_game` | 关闭游戏 | `am force-stop` 强制关闭游戏进程 |
| `none` | 不停止 | 仅 `fatigue_action` 可取：体力不足时不触发停止（默认） |

停止触发场景：
- 跑商全部轮次完成
- 归位/轮次失败 → 直接 `return`（不再有失败退出开关）
- 疲劳 + `fatigue_action != "none"` → 设 STOP
- 用户点击前端「停止」
- `StopExecution` 异常

以上任意场景的退出路径都会走到 `_transition_locked` / `_run_page_flow_locked` 的 `try/finally`。`finally` 中按以下优先级执行 **一次** 后置动作：

1. 若疲劳触发停止（`_fatigue_action` 已设置）→ 执行 `_execute_action(fatigue_action)`，并清空 `_fatigue_action`
2. 否则 → 执行 `_execute_on_stop_action()`（即 `on_stop_action`）

即 `fatigue_action` 优先于 `on_stop_action`：疲劳导致的停止按 `fatigue_action` 处置，其余停止场景按 `on_stop_action` 处置。两者都只决定 **停止后对游戏做什么**，不决定是否停止脚本。

## 恢复与纠错

**轻量 guard 优先，失败才 recovery**：

```
业务步骤入口 → guard 检查 Scene 可用
  → 是：直接继续
  → 否：recover_to_expected()
```

`recover_to_expected()` 处理：登录页、加载/转场、公告弹窗、崩溃、行车中、误触页 → 最终回到目标 Scene。

## Scenes

| Scene | 说明 | 优先级 |
|-------|------|--------|
| CRASH | 游戏崩溃 | 最高 |
| LOGIN / LOADING / TRANSIT | 登录、加载、转场 | 高 |
| MAIN_MAP | 大地图 | 中 |
| CITY_VIEW | 城市页面 | 中 |
| EXCHANGE / EXCHANGE_BUY / EXCHANGE_SELL | 交易所 | 中 |
| STATION_LIST / STATION_DETAIL | 站点列表/详情 | 中 |
| TRAVEL_CRUISE / TRAVEL_MAP | 行车中 | 低 |
| BATTLE_CARD / BATTLE_RESULT | 战斗 | 低 |

## 关键 API

```
设备:  GET  /api/device/scan|status
       POST /api/device/connect|start-game|stop-game|restart-game
       POST /api/device/benchmark-screenshot
跑商:  GET  /api/business/cities
       POST /api/business/start|stop
场景:  GET  /api/status/scene
配置:  GET  /api/config/get|city-config
       POST /api/config/save|city-config
调度:  GET  /api/scheduler/status
       POST /api/scheduler/start|stop
调试:  POST /api/debug/snapshot|trade-page-flow
       GET  /api/debug/logs|files/<name>
```

详情见 `README.md` 或各 route 文件。
