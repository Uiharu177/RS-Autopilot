import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Business from '../views/Business.vue'
import DeviceConfig from '../views/DeviceConfig.vue'
import Settings from '../views/Settings.vue'
import DebugTools from '../views/DebugTools.vue'
import About from '../views/About.vue'

const routes = [
  { path: '/', component: Home, meta: { title: '控制中心' } },
  { path: '/business', component: Business, meta: { title: '路线编排' } },
  { path: '/device', component: DeviceConfig, meta: { title: '设备配置' } },
  { path: '/settings', component: Settings, meta: { title: '系统设置' } },
  { path: '/debug', component: DebugTools, meta: { title: '开发调试' } },
  { path: '/about', component: About, meta: { title: '关于' } },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
