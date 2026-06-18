# RS-Autopilot 架构与操作逻辑

## 技术栈

Python 3.12 / Flask + simple-websocket / Vue 3 + Naive UI
ONNX PaddleOCR / OpenCV / ADB / MuMu IPC

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
Device → ADB / NEMU IPC
```

### 各层职责

| 层 | 职责 |
|---|------|
| Device | 统一接口：截图、点击、启动/关闭游戏。NEMU 连接分段化——`connect()` 只拿 IPC 连接，display_id 首次截图时懒加载 |
| Vision | ONNX OCR 裁剪/缓存、模板匹配、BGR/HSV 颜色判断 |
| Scene | 级联 detector 识别当前页面，场景转移图引导恢复 |
| Solvers | boot (万能启动)、trade (环线/端点跑商编排)、navigation (地图导航/行车监听)、recovery (接管/纠错) |
| Scheduler | 线程内任务执行 + STOP 标志位控制 |
| Server | REST API + WebSocket 日志/截图推送 |

## 设备连接策略

### NEMU 懒加载

截图/触控方式选 NEMU 时：
1. `connect()` → `nemu_connect` 获取 IPC 连接，成功即返回
2. `check_status()` 只检查 `connect_id > 0`，不要求 display_id
3. 首次 `screenshot()` / `input_tap()` → `_ensure_display()` → `_acquire_display()` 获取 display_id + 分辨率
4. 游戏未运行 → display_id < 0 → `ConnectionError` → 上级 catch 后降级到 ADB
5. 游戏启动后 → 下次操作自动拿到 display_id → 切回 NEMU IPC

### STOP 守卫

`kill()` → `am force-stop` + `STOP = True` + `_is_connected = False`。此后：
- `_ensure_connected()` 检测 `STOP` 直接返回，不重连、不清标志
- `NEMU.connect()` 不再内部 auto-start 游戏（启动权在 `boot_game()`）
- 前端轮询 `/status/scene` 时截图失败返回 409，不触发重连

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

每城一次（卖货后买货前），通过三个开关独立控制：

```
体力检查通过？→ 继续
体力不足：
  use_stamina_item? → 尝试使用道具 → 成功继续 / 失败走下一步
  is_exit_on_fatigue? → kill() + STOP
  两开关都关 → warning 继续（影响议价）
```

### 停止信号

STOP 标志位检查点：
- `_transition_locked` 每轮前
- `_run_page_flow_locked` 轮间
- `screenshot()` / `screenshot_image()` 入口
- 导航、交易所等主要操作边界

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
