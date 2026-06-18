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
        <n-text strong>RS-Autopilot</n-text>（RS自动驾驶）是《雷索纳斯》(Resonance Solstice) 手游的自动化工具，支持自动跑商相关的核心玩法。
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
        <n-li><strong>Python</strong>: 3.11 或 3.12</n-li>
        <n-li><strong>Node.js</strong>: 18+（前端需要）</n-li>
        <n-li><strong>模拟器</strong>: <n-a href="https://mumu.163.com/mumu12/" target="_blank">MuMu 模拟器 12</n-a></n-li>
      </n-ul>

      <n-h2>快速开始</n-h2>
      <n-list bordered style="margin-bottom: 16px">
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">1</n-tag></template>
          <div><strong>安装 Python 依赖</strong>：在项目根目录运行 <n-text code>pip install -e .</n-text></div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">2</n-tag></template>
          <div><strong>启动服务</strong>：运行 <n-text code>start.bat</n-text> 一键启动后端和前端。</div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">3</n-tag></template>
          <div><strong>配置模拟器</strong>：打开「设备配置」页面，点击「扫描模拟器」，找到你的设备后点击「使用此设备」。</div>
        </n-list-item>
        <n-list-item>
          <template #prefix><n-tag size="small" type="primary">4</n-tag></template>
          <div><strong>开始跑商</strong>：在「路线编排」设置好城市和次数，回到「控制中心」启动。</div>
        </n-list-item>
      </n-list>

      <n-h2>CLI 命令</n-h2>
      <n-table :bordered="false" :single-line="false" size="small" style="margin-bottom: 16px">
        <thead>
          <tr><th style="width: 200px">命令</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td><n-text code>resonance scan</n-text></td><td>扫描本机运行中的模拟器</td></tr>
          <tr><td><n-text code>resonance connect --port 16384</n-text></td><td>测试指定端口的 ADB 连接</td></tr>
          <tr><td><n-text code>resonance screenshot</n-text></td><td>执行一次截图测试（含 OCR 识别）</td></tr>
          <tr><td><n-text code>resonance start-game</n-text></td><td>启动游戏应用</td></tr>
          <tr><td><n-text code>resonance stop-game</n-text></td><td>强制关闭游戏应用</td></tr>
          <tr><td><n-text code>resonance serve</n-text></td><td>启动 Web 后端 API 服务</td></tr>
        </tbody>
      </n-table>

      <n-h2>Web 控制台</n-h2>
      <n-table :bordered="false" :single-line="false" style="margin-bottom: 16px">
        <thead>
          <tr><th>页面</th><th>路由</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td>控制中心</td><td><n-text code>/</n-text></td><td>状态面板、实时日志、截图预览、任务启停</td></tr>
          <tr><td>路线编排</td><td><n-text code>/business</n-text></td><td>端点/环线跑商配置</td></tr>
          <tr><td>设备配置</td><td><n-text code>/device</n-text></td><td>模拟器扫描、连接、测速、游戏启停</td></tr>
          <tr><td>系统设置</td><td><n-text code>/settings</n-text></td><td>体力药、疲劳保护等自动化偏好</td></tr>
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
          <tr><td><n-text code>docs/</n-text></td><td>架构文档</td></tr>
        </tbody>
      </n-table>

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
