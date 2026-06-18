import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './style.css'

function showRuntimeError(error: unknown) {
  const appRoot = document.getElementById('app')
  const text = error instanceof Error ? `${error.name}: ${error.message}\n${error.stack || ''}` : String(error)
  if (appRoot) {
    appRoot.innerHTML = `<pre style="box-sizing:border-box;margin:0;padding:24px;min-height:100vh;background:#1f1f1f;color:#ffb4b4;white-space:pre-wrap;font:14px/1.5 Consolas,monospace;">Frontend runtime error:\n\n${text.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] || c))}</pre>`
  }
}

window.addEventListener('error', (event) => showRuntimeError(event.error || event.message))
window.addEventListener('unhandledrejection', (event) => showRuntimeError(event.reason))

try {
  const app = createApp(App)
  app.config.errorHandler = (error) => showRuntimeError(error)
  app.use(createPinia())
  app.use(router)
  app.use(naive)
  app.mount('#app')
} catch (error) {
  showRuntimeError(error)
}
