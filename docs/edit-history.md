# 变更日志

## 2026-07

### 07-02

#### 停止与杀游戏解耦（on_stop_action）

- **新增配置** `on_stop_action`（`stay_there` / `goto_main` / `close_game`）
- **移除业务逻辑中所有 inline `kill()`**：`_takeover_current_city`、`_check_strength_and_use`、`_transition_locked` 中 5 处 `kill()` 全部删除
- `_transition_locked` / `_run_page_flow_locked` 添加 `try/finally`，finally 中执行 `_execute_on_stop_action()`
- `is_exit_on_failure` 和 `is_exit_on_fatigue` 只控制是否停止脚本，不再附带杀游戏
- `_cleanup_game()` 作为私有方法保留，仅当 `on_stop_action == "close_game"` 时调用

#### 截图/触控方式扩展

- **DroidCast 截图**：`resonance/device/droidcast.py`，HTTP Java 服务器截图，触控委托 ADB
- **Scrcpy 截图+触控**：`resonance/device/scrcpy.py`，H.264 视频流 + 控制 socket
- `ScreenshotMethod` 枚举新增 `droidcast`、`scrcpy`
- `TouchMethod` 枚举新增 `scrcpy`
- `device.py` `connect()` 按优先级选设备：**Scrcpy > NEMU > DroidCast > ADB**，失败自动降级
- 新增 `_pick_device()` 函数
- 前端 DeviceConfig/Settings 截图和触控方式改为下拉选择框
- `pyproject.toml` 新增 `[project.optional-dependencies] scrcpy = ["av>=12.0.0"]`

#### 前端完善

- **`running` 状态同步**：Business.vue 每 3 秒轮询 `api.scheduler.status()`
- **游戏控制按钮**：DeviceConfig 页面新增 `[启动游戏] [关闭游戏] [重启游戏]`
- **截图方式状态**：DeviceConfig 显示当前实际使用的截图后端
- **`autoSnapshot` 预览**：WebSocket 推截图时只在实际勾选时才创建 blob URL，组件卸载时清理
- **Setting.vue**：触控方式独立选择器，修复 `saveDeviceConfig` 触控方式被复制为截图方式的 bug

#### Scheduler 完善

- 任务全部完成后自动停止（`_running=False` + `_stop_event.set()`）
- Scene API idle 守卫：scheduler 未运行时返回 `{idle: true}`，不截图

#### 截图容错

- NEMU.screenshot() 失败返回 `None` 而非抛异常
- `screenshot_image()` 静默 fallback 到 ADB
- `save_screenshot()` 参数改为 Optional

#### 项目整理

- 删除嵌套副本 `resonance/resonance/`、`web/web/`（含重复 node_modules，释放 157MB）、`resources/resources/`
- 删除根目录旧日志 `serve_stderr.log`、`serve_stdout.log`、`stderr.log`、`stdout.log`
- 创建 `resources/vendor/` 目录（预留 DroidCast APK / scrcpy-server.jar）
- 新增 `docs/ai-agent-setup.md`（AI Agent 安装提示词）

### 06-27

#### 跑商编排优化

- **环线模式**：支持 N 城循环，自动对齐到当前城市
- **归位优化**：环线首城先 `_sell_current_goods(0)` 清空车厢
- **体力检查重构**：`_check_strength_and_use()` 三个开关独立生效。两开关都关时 warning + 继续（不阻塞流程）
- **导航守卫**：EXCHANGE 预处理 → `leave_exchange()` → 重判，统一解决交易所残留
- **多轮 STOP 检测**：`_run_page_flow_locked` 轮间检测 `device_state.STOP`
- **清理死代码**：删除 `use_book`、`_is_exchange_screen` 等无用函数和 import

### 设备层

- **NEMU 连接分段化**：`connect()` 只获取 IPC 连接，display_id 首次截图时懒加载
- **移除 NEMU 内部 auto-start**：`NEMU.connect()` 不在 display_id < 0 时自动启动游戏
- **STOP 守卫**：`_ensure_connected()` 检测 STOP 直接返回，传 `reset_stop=False`
- **改进 `kill()`**：`am force-stop` 实际关闭游戏进程，重置 `_is_connected` 和 `_display_ready`
- **截图回退**：NEMU.screenshot() 返回 None 不抛异常，screenshot_image() 静默 fallback

## 2026-06

### 06-18

- **WebSocket 初始日志修复**：`construct_initial()` 优先从内存 `log_lines` 取历史；前端批量/单行区分，重连不重复追加
- **脚本安全加固**：`start.bat` 窗口标题精确匹配；端口清理增加进程身份验证；`stop.bat` 端口精确匹配
- **README 部署流程修正**：调整为先启动后配置的顺序
