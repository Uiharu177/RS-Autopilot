<template>
  <n-config-provider :theme-overrides="themeOverrides" :hljs="hljs">
    <n-message-provider>
      <n-notification-provider>
        <n-dialog-provider>
        <div class="app-bg" />
        <n-layout :has-sider="!mobile" style="height: 100vh; background: transparent" class="outer-layout">
        <n-layout-sider
          v-if="!mobile"
          bordered
          :width="220"
          :native-scrollbar="false"
          style="background: rgba(255,255,255,0.9); backdrop-filter: blur(12px); box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05)"
          class="glass-sider"
        >
          <div class="sider-wrapper">
            <div class="sider-header">
              <div class="sider-logo">
                <div class="logo-box">
                  <n-icon size="20" color="#fff"><TrainOutline /></n-icon>
                </div>
                <div>
                  <div class="logo-title">RS-Autopilot</div>
                  <div class="logo-sub">RS自动驾驶</div>
                </div>
              </div>
            </div>
            <n-menu
              :value="route.path"
              :options="menuOptions"
              :indent="20"
              class="sider-menu"
              @update:value="handleMenuSelect"
            />
            <div class="sider-footer">
              <n-tag :type="runtime.connected ? 'success' : 'error'" round :bordered="false" size="small">
                {{ runtime.connected ? '设备已连接' : '设备未连接' }}
              </n-tag>
            </div>
          </div>
        </n-layout-sider>
          <n-layout-content style="background: transparent; overflow: hidden" class="layout-content-container">
            <router-view />
          </n-layout-content>
          <n-layout-footer v-if="mobile" bordered position="static" style="background: rgba(255,255,255,0.9); backdrop-filter: blur(12px);">
            <div class="mobile-tab-bar">
              <div v-for="item in mobileTabs" :key="item.key" class="mobile-tab" :class="{ active: route.path === item.key }" @click="handleMenuSelect(item.key)">
                <n-icon size="22"><component :is="item.icon" /></n-icon>
                <span class="mobile-tab-label">{{ item.label }}</span>
              </div>
            </div>
          </n-layout-footer>
        </n-layout>
        </n-dialog-provider>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { h, ref, onMounted, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import hljs from '@/utils/hljs'
import type { GlobalThemeOverrides, MenuOption } from 'naive-ui'
import { NIcon } from 'naive-ui'
import {
  HomeOutline,
  TrainOutline,
  SettingsOutline,
  EyeOutline,
  PhonePortraitOutline,
  InformationCircleOutline,
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const runtime = useRuntimeStore()

const mobile = ref(window.innerWidth < 800)
provide('mobile', mobile)

onMounted(() => {
  const onResize = () => { mobile.value = window.innerWidth < 800 }
  window.addEventListener('resize', onResize)
})

const themeOverrides: GlobalThemeOverrides = {
  common: {
    fontFamily: 'var(--sans)',
    bodyColor: 'transparent',
    cardColor: 'rgba(255, 255, 255, 0.85)',
    baseColor: 'transparent',
    textColorBase: '#111827',
    textColor1: '#111827',
    textColor2: '#4b5563',
    textColor3: '#6b7280',
    borderColor: '#e5e7eb',
    primaryColor: '#3b82f6',
    primaryColorHover: '#2563eb',
    primaryColorPressed: '#1d4ed8',
    primaryColorSuppl: '#60a5fa',
    infoColor: '#0ea5e9',
    successColor: '#10b981',
    warningColor: '#f59e0b',
    errorColor: '#ef4444',
    borderRadius: '12px',
  },
  Layout: {
    color: 'transparent',
    siderColor: 'transparent',
    textColor: '#111827',
  },
  Card: {
    borderRadius: '12px',
    color: 'rgba(255, 255, 255, 0.85)',
    titleFontWeight: '600',
    titleTextColor: '#111827',
    textColor: '#374151',
    borderColor: '#e5e7eb',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  },
  Menu: {
    itemTextColor: '#4b5563',
    itemTextColorActive: '#2563eb',
    itemTextColorHover: '#111827',
    itemColorActive: '#eff6ff',
    itemColorActiveHover: '#dbeafe',
    borderRadius: '12px',
    itemHeight: '42px',
  },
  Button: {
    textColorPrimary: '#ffffff',
    textColorHoverPrimary: '#ffffff',
    textColorPressedPrimary: '#ffffff',
    textColorFocusPrimary: '#ffffff',
    textColorInfo: '#ffffff',
    textColorHoverInfo: '#ffffff',
    textColorPressedInfo: '#ffffff',
    textColorFocusInfo: '#ffffff',
    textColorSuccess: '#ffffff',
    textColorHoverSuccess: '#ffffff',
    textColorPressedSuccess: '#ffffff',
    textColorFocusSuccess: '#ffffff',
    textColorWarning: '#ffffff',
    textColorHoverWarning: '#ffffff',
    textColorPressedWarning: '#ffffff',
    textColorFocusWarning: '#ffffff',
    textColorError: '#ffffff',
    textColorHoverError: '#ffffff',
    textColorPressedError: '#ffffff',
    textColorFocusError: '#ffffff',
  },
};

function makeIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: '控制中心', key: '/', icon: makeIcon(HomeOutline) },
  { label: '路线编排', key: '/business', icon: makeIcon(TrainOutline) },
  { label: '设备配置', key: '/device', icon: makeIcon(PhonePortraitOutline) },
  { label: '系统设置', key: '/settings', icon: makeIcon(SettingsOutline) },
  { label: '开发调试', key: '/debug', icon: makeIcon(EyeOutline) },
  { label: '关于', key: '/about', icon: makeIcon(InformationCircleOutline) },
]

const mobileTabs = [
  { label: '控制中心', key: '/', icon: HomeOutline },
  { label: '路线编排', key: '/business', icon: TrainOutline },
  { label: '设备配置', key: '/device', icon: PhonePortraitOutline },
  { label: '系统设置', key: '/settings', icon: SettingsOutline },
  { label: '关于', key: '/about', icon: InformationCircleOutline },
]

function handleMenuSelect(key: string) {
  router.push(key)
}
</script>

<style scoped>
.app-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  background: url('https://img.zcool.cn/community/0150965e1ce0bca801216518471b48.jpg@1280w_1l_2o_100sh.jpg') no-repeat center center;
  background-size: cover;
}

.glass-sider {
  display: flex;
  flex-direction: column;
}

.sider-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sider-header {
  padding: 24px 20px 16px;
  flex-shrink: 0;
}

.sider-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-box {
  width: 32px;
  height: 32px;
  background: #2563eb;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-title {
  font-weight: 700;
  font-size: 18px;
  color: #111827;
  letter-spacing: -0.5px;
}

.logo-sub {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.sider-menu {
  flex: 1;
  overflow-y: auto;
}

.sider-footer {
  flex-shrink: 0;
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.mobile-tab-bar {
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 56px;
}

.mobile-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: 6px 12px;
  color: #94a3b8;
  transition: color 0.2s;
}

.mobile-tab.active {
  color: #2563eb;
}

.mobile-tab-label {
  font-size: 11px;
  font-weight: 500;
  line-height: 1;
}
</style>

<style>
.n-menu-item--selected,
.n-menu-item--selected:hover {
  position: relative;
}
.n-menu-item--selected::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background: #2563eb;
  border-radius: 0 2px 2px 0;
}

.outer-layout > .n-layout-scroll-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.layout-content-container > .n-layout-scroll-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.n-card:not(.n-modal .n-card) {
  backdrop-filter: blur(12px);
}
</style>
