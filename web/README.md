# Web 前端

Vue 3 + TypeScript + Vite + Naive UI。

## 开发

```bash
cd web
npm install
npm run dev     # 开发服务器 :5173
npm run build   # 生产构建 → dist/
```

Vite proxy 将 `/api` 和 `/socket.io` 转发到 `http://127.0.0.1:5000`。

## 路由

| 路由 | 视图 | 说明 |
|------|------|------|
| `/` | Home | 当前 Scene + 设备状态 |
| `/business` | Business | 跑商配置与启停 |
| `/device` | DeviceConfig | 设备连接与截图方式 |
| `/settings` | Settings | 全局设置与调试入口 |
| `/logs` | LogViewer | WebSocket 实时日志 |

## 后端 API

详见 `docs/architecture.md`。
