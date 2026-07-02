# Web 前端

Vue 3 + TypeScript + Vite + Naive UI。

## 环境要求

- **Node.js**: 18+ — [下载](https://nodejs.org/)
- **Python 后端**: 需先按项目根目录 README 完成 Python 环境与依赖安装

## 快速开始

### 1. 安装前端依赖
```
cd web
npm install
```

### 2. 启动后端
前端开发需要后端在 `http://127.0.0.1:15177` 运行，请在项目根目录另开一个终端：
```
python cli.py serve
```

### 3. 启动开发服务器
```
npm run dev
```
开发服务器默认 `http://localhost:5173`，前端通过 CORS 直连后端，API 前缀 `/api`，WebSocket 走 `ws://127.0.0.1:15177/ws`，无需 Vite proxy。

## 构建

```
npm run build
```
产物输出到 `dist/`，由后端 Flask 托管，生产环境无需 Node.js，访问 `http://127.0.0.1:15177` 即可。

## 路由

| 路由 | 视图 | 说明 |
|------|------|------|
| `/` | Home | 当前 Scene + 设备状态 |
| `/business` | Business | 跑商配置与启停 |
| `/device` | DeviceConfig | 设备连接与截图方式 |
| `/settings` | Settings | 全局设置与调试入口 |
| `/debug` | DebugTools | 日志回放、截图时间线 |
| `/about` | About | 项目说明与免责声明 |

## 后端 API

详见 `docs/architecture.md` 和 `docs/add-station-guide.md`。