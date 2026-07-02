<template>
  <div class="page-container" style="position: relative">
    <div style="position: absolute; top: 16px; right: 16px; z-index: 10; display: flex; flex-direction: column; align-items: flex-end; gap: 10px">
      <n-a href="https://github.com/Uiharu177/RS-Autopilot" target="_blank" style="font-size: 15px; color: #64748b; text-decoration: none; font-weight: 600">
        Uiharu177/RS-Autopilot ↗
      </n-a>
      <n-space>
        <n-button size="small" tag="a" href="https://github.com/Uiharu177/RS-Autopilot" target="_blank" secondary>
          GitHub
        </n-button>
        <n-button size="small" tag="a" href="https://space.bilibili.com/382780205" target="_blank" secondary type="info">
          B站
        </n-button>
      </n-space>
    </div>
    <n-card :bordered="false" style="max-width: 800px">
      <n-h1>RS-Autopilot — RS自动驾驶</n-h1>
      <n-p>
        <n-text strong>RS-Autopilot</n-text>（RS自动驾驶）是《雷索纳斯》(Resonance Solstice) 手游的自动化工具，支持自动跑商相关的核心玩法。技术栈：Python / Flask / ADB / MuMu IPC / DroidCast / Scrcpy / OCR / Vue 3
      </n-p>

      <n-divider />

      <n-alert type="warning" :bordered="false" style="margin-bottom: 16px">
        <template #header>免责声明</template>
        <n-ul style="margin: 8px 0 0 0; padding-left: 20px">
          <n-li>本项目仅用于 <strong>学习和研究</strong> 目的，严禁用于商业用途或破坏游戏公平性的行为。</n-li>
          <n-li>使用本项目产生的任何后果（包括但不限于账号封禁、数据丢失等）由使用者自行承担，项目开发者不承担任何责任。</n-li>
          <n-li>本项目与《雷索纳斯》官方无任何关联，未取得任何官方授权。</n-li>
        <n-li>使用前请仔细阅读游戏用户协议，确认是否允许第三方自动化工具。</n-li>
        <n-li>如游戏官方要求停止，本项目将立即下架并删除所有相关内容。</n-li>
        <n-li>本项目 <strong>由 AI 生成</strong>，代码质量不保证，使用前请自行审查代码。</n-li>
        <n-li><strong>beta 阶段</strong> — API 和配置格式可能随时变化，不保证向后兼容。</n-li>
        <n-li>本人无力维护，请自行解决遇到的问题。</n-li>
        </n-ul>
        <n-text depth="3" style="margin-top: 8px; display: block">继续使用即代表你同意以上条款。</n-text>
      </n-alert>

      <n-h2>环境要求</n-h2>
      <n-ul>
        <n-li><strong>OS</strong>: Windows 10/11</n-li>
        <n-li><strong>Python</strong>: 3.11 或 3.12 — <n-a href="https://www.python.org/downloads/" target="_blank">下载</n-a>（安装时勾选"Add Python to PATH"）</n-li>
        <n-li><strong>Node.js</strong>: 18+ — <n-a href="https://nodejs.org/" target="_blank">下载</n-a></n-li>
        <n-li><strong>模拟器</strong>: <n-a href="https://mumu.163.com/mumu12/" target="_blank">MuMu 模拟器 12</n-a></n-li>
      </n-ul>

      <n-h2>快速开始</n-h2>
      <n-p depth="3" style="margin-bottom: 12px">遇到问题时，如有必要可寻求 AI 帮助，把报错信息和当前操作贴给 AI 通常能快速定位问题。可将 docs/ai-agent-setup.md 喂给 agent 帮你安装。</n-p>
      <n-list bordered style="margin-bottom: 16px">
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">1</n-tag></template>
          <div><strong>克隆项目</strong></div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：你希望存放的位置</div>
          <div>克隆仓库并进入项目目录：</div>
          <div><n-text code>git clone https://github.com/Uiharu177/RS-Autopilot.git</n-text></div>
          <div><n-text code>cd RS-Autopilot</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">2</n-tag></template>
          <div><strong>安装 Python</strong>：下载并安装 Python 3.11 或 3.12，安装时勾选 "Add Python to PATH"。</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：任意</div>
          <div>验证安装：</div>
          <div><n-text code>python --version</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">3</n-tag></template>
          <div><strong>安装 Node.js</strong>：下载并安装 Node.js 18 或更高版本（用于首次构建前端，运行时不需要）。</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：任意</div>
          <div>验证安装：</div>
          <div><n-text code>node --version</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">4</n-tag></template>
          <div><strong>安装 Python 依赖</strong></div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：项目根目录</div>
          <div>升级 pip（可选）：</div>
          <div><n-text code>python -m pip install --upgrade pip</n-text></div>
          <div>安装项目依赖：</div>
          <div><n-text code>pip install -r requirements.txt</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">5</n-tag></template>
          <div><strong>启动</strong>：会自动安装前端依赖、构建前端、启动后端服务（端口 15177，前端由后端托管）并打开浏览器 http://127.0.0.1:15177/#/</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：项目根目录</div>
          <div><n-text code>start.bat</n-text></div>
          <div>备选：仅启动后端 API（不含前端界面）</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：项目根目录</div>
          <div><n-text code>python cli.py serve</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">6</n-tag></template>
          <div><strong>配置模拟器</strong>：浏览器打开后进入「设备配置」→「扫描」→ 选中模拟器 →「使用此设备」；或启动前手动复制 <n-text code>config/app.example.json</n-text> 为 <n-text code>config/app.json</n-text> 填写设备信息。</div>
        </n-list-item>
      </n-list>

      <n-h2>端口被占用？</n-h2>
      <n-p>项目默认使用端口 <n-text code>15177</n-text>，若该端口被其他程序占用，可修改以下两处改为空闲端口：</n-p>
      <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">后端端口（<n-text code>cli.py</n-text> 的 <n-text code>app.run(...)</n-text> 一行）</div>
      <div><n-text code>app.run(host="127.0.0.1", port=15177, debug=False, use_reloader=False)</n-text></div>
      <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">前端 API/WebSocket 地址（<n-text code>web/src/api/index.ts</n-text> 前两行）</div>
      <div><n-text code>export const API_ORIGIN = 'http://127.0.0.1:15177'</n-text></div>
      <div><n-text code>export const WS_ORIGIN = 'ws://127.0.0.1:15177'</n-text></div>
      <n-p depth="3">修改后需在 <n-text code>web/</n-text> 目录重新执行 <n-text code>npm run build</n-text>，再 <n-text code>start.bat</n-text> 生效。</n-p>

      <n-h2>更新</n-h2>
      <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：项目根目录</div>
      <div>拉取最新代码：</div>
      <div><n-text code>git pull</n-text></div>
      <div>更新 Python 依赖：</div>
      <div><n-text code>pip install -r requirements.txt</n-text></div>
      <div>安装前端依赖并重新构建：</div>
      <div><n-text code>cd web</n-text></div>
      <div><n-text code>npm install</n-text></div>
      <div><n-text code>npm run build</n-text></div>
      <div><n-text code>cd ..</n-text></div>
      <n-p depth="3">重新执行 <n-text code>start.bat</n-text> 即可重新启动。</n-p>

      <n-h2>Web 控制台</n-h2>
      <n-table :bordered="false" :single-line="false" style="margin-bottom: 16px">
        <thead>
          <tr><th>页面</th><th>路由</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td>控制中心</td><td><n-text code>/</n-text></td><td>状态面板、实时日志、截图预览、任务启停</td></tr>
          <tr><td>路线编排</td><td><n-text code>/business</n-text></td><td>端点/环线跑商配置</td></tr>
          <tr><td>设备配置</td><td><n-text code>/device</n-text></td><td>模拟器扫描、连接、测速、游戏启停</td></tr>
          <tr><td>系统设置</td><td><n-text code>/settings</n-text></td><td>体力药、停止条件、停止后动作等自动化偏好</td></tr>
          <tr><td>开发调试</td><td><n-text code>/debug</n-text></td><td>日志回放、截图时间线</td></tr>
          <tr><td>关于</td><td><n-text code>/about</n-text></td><td>项目说明与免责声明</td></tr>
        </tbody>
      </n-table>

      <n-h2>已知问题</n-h2>
      <n-ul>
        <n-li>日志输出不够清晰</n-li>
        <n-li>UI 比较简陋（尽力了）</n-li>
        <n-li>AI 生成的代码可能产生各种莫名其妙的 Bug</n-li>
      </n-ul>

      <n-h2>项目结构</n-h2>
      <n-table :bordered="false" :single-line="false" size="small" style="margin-bottom: 16px">
        <thead>
          <tr><th style="width: 200px">路径</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td><n-text code>cli.py</n-text></td><td>CLI 入口</td></tr>
          <tr><td><n-text code>resonance/</n-text></td><td>Python 后端</td></tr>
          <tr><td><n-text code>  device/</n-text></td><td>ADB / MuMu IPC 设备控制</td></tr>
          <tr><td><n-text code>  vision/</n-text></td><td>OCR 识别、模板匹配</td></tr>
          <tr><td><n-text code>  scene/</n-text></td><td>场景识别系统</td></tr>
          <tr><td><n-text code>  solvers/</n-text></td><td>业务逻辑（跑商、导航、恢复）</td></tr>
          <tr><td><n-text code>  scheduler/</n-text></td><td>后台任务调度</td></tr>
          <tr><td><n-text code>  server/</n-text></td><td>Flask API + WebSocket</td></tr>
          <tr><td><n-text code>web/</n-text></td><td>Vue 3 前端（RS自动驾驶控制台）</td></tr>
          <tr><td><n-text code>resources/</n-text></td><td>游戏数据、图片模板</td></tr>
          <tr><td><n-text code>config/</n-text></td><td>运行时配置</td></tr>
          <tr><td><n-text code>docs/</n-text></td><td>文档目录</td></tr>
          <tr><td><n-text code>docs/architecture.md</n-text></td><td>系统架构与操作逻辑说明</td></tr>
          <tr><td><n-text code>docs/add-station-guide.md</n-text></td><td>新增站点完整教程（坐标标定、商品/疲劳数据填写）</td></tr>
        </tbody>
      </n-table>

      <n-h2>卸载</n-h2>
      <n-list bordered style="margin-bottom: 16px">
        <n-list-item>
          <template #prefix><n-tag size="small" type="warning">1</n-tag></template>
          <div><strong>停止服务</strong>：或关闭所有 RS-Autopilot 命令行窗口。</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：项目根目录</div>
          <div><n-text code>stop.bat</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="warning">2</n-tag></template>
          <div><strong>卸载 Python 依赖（可选）</strong></div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：任意</div>
          <div><n-text code>pip uninstall -y Pillow loguru numpy opencv-python orjson pydantic watchdog adb-shell onnxocr-ppocrv4 requests psutil onnxruntime flask flask-cors flask-sock simple-websocket networkx pyyaml</n-text></div>
          <div>如安装时额外装了 scrcpy 可选依赖，可一并卸载：</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">执行路径：任意</div>
          <div><n-text code>pip uninstall -y av</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="warning">3</n-tag></template>
          <div><strong>删除项目目录</strong>：直接删除整个 RS-Autopilot 文件夹即可，所有配置和日志都在该目录内。</div>
          <div style="color: #94a3b8; font-size: 13px; margin: 4px 0">可能导致的后果：已保存的跑商路线/城市配置、运行日志、调试截图都会丢失；如需保留请先备份 <n-text code>config/</n-text> 和 <n-text code>logs/</n-text> 目录。</div>
          <div>MuMu 模拟器与游戏本身不受影响，如需卸载请另行处理。</div>
        </n-list-item>
      </n-list>

      <n-h2>致谢</n-h2>
      <n-p>
        功能参考自 <n-a href="https://github.com/Night-stars-1/Auto_Resonance" target="_blank">Auto_Resonance</n-a> 项目，感谢原作者的贡献。
      </n-p>

      <n-h2>License</n-h2>
      <n-tag type="default">MIT</n-tag>
    </n-card>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.page-container {
  height: 100%;
  padding: 12px;
  overflow-y: auto;
}

.n-h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.n-h2 {
  font-size: 20px;
  margin-top: 24px;
  margin-bottom: 12px;
}
</style>
