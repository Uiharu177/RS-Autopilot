# 变更日志

## 2026-06

### 设备层

- **NEMU 连接分段化**：`connect()` 只获取 IPC 连接（connect_id），display_id 首次截图/触控时懒加载。`check_status()` 只检查 connect_id > 0
- **移除 NEMU 内部 auto-start**：`NEMU.connect()` 不再在 display_id < 0 时自动通过 ADB monkey 启动游戏，启动权统一在 `boot_game()` 中
- **STOP 守卫**：`_ensure_connected()` 检测 STOP 直接返回，传 `reset_stop=False` 不清理停止标志
- **改进 `kill()`**：`am force-stop` 实际关闭游戏进程，重置 `_is_connected` 和 `_display_ready`

### 前端

- **`running` 状态自动同步**：Business.vue 每 3 秒轮询 `api.scheduler.status()`，任务完成后自动将 running 置为 false
- **游戏控制按钮**：DeviceConfig 页面新增 `[启动游戏] [关闭游戏] [重启游戏]`
- **截图方式状态**：DeviceConfig 显示当前实际使用的截图后端（NEMU/ADB）
- **预览截图优化**：勾选后显示布局占位，WebSocket 推截图时只在实际勾选时才创建 blob URL，组件卸载时清理

### 跑商编排

- **环线模式**：支持 N 城循环（自动对齐到当前城市）
- **归位优化**：环线首城先 `_sell_current_goods(0)` 清空车厢
- **体力检查重构**：`_check_strength_and_use()` 三个开关独立生效（use_stamina_item / is_exit_on_fatigue / is_exit_on_failure）。两开关都关时 warning + 继续（不阻塞流程）
- **导航守卫**：EXCHANGE 预处理 → `leave_exchange()` → 重判，统一解决交易所残留
- **多轮 STOP 检测**：`_run_page_flow_locked` 轮间检测 `device_state.STOP`
- **清理死代码**：删除 `use_book`、`_is_exchange_screen` 等无用函数和 import

### CLI

- `cli.py serve` 启动后端服务，`scanner` 扫描模拟器

### 日志

- `logger.debug("体力检查通过")` 保持 debug 级别
- 各决策点（体力不足、道具使用、疲劳触发）都有 log 输出
