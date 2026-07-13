<template>
  <div class="home-container">
    <div v-if="autoSnapshot" class="top-block">
      <div class="sc-wrapper">
        <n-image
          v-if="snapshotImageUrl"
          preview-disabled
          width="100%"
          height="100%"
          class="sc"
          :src="snapshotImageUrl"
          object-fit="cover"
        />
        <div v-else class="sc-placeholder">等待截图...</div>
      </div>
      <div class="stat-bar">
        <div v-for="stat in stats" :key="stat.label" class="stat-chip">
          <n-icon :size="14" :color="stat.color"><component :is="stat.icon" /></n-icon>
          <span class="stat-chip-label">{{ stat.label }}</span>
          <span class="stat-chip-value">{{ stat.value }}</span>
        </div>
      </div>
    </div>

    <div v-else class="stat-chips">
      <div v-for="stat in stats" :key="stat.label" class="stat-chip">
          <n-icon :size="14" :color="stat.color"><component :is="stat.icon" /></n-icon>
        <span class="stat-chip-label">{{ stat.label }}</span>
        <span class="stat-chip-value">{{ stat.value }}</span>
      </div>
    </div>

    <div v-if="runtime.currentStep" class="step-row">
      <span class="step-arrow">>></span>
      <span class="step-text">{{ runtime.currentStep }}</span>
    </div>

    <div class="log-display">
      <LogTerminal :limit="150" :auto-scroll="autoScrollLog" />
      <div class="log-spacer" />
    </div>

    <div class="action-container">
      <n-button
        v-if="runtime.schedulerRunning"
        type="error"
        :loading="schedulerLoading"
        :disabled="schedulerLoading"
        @click="stopScheduler"
      >
        停止运行
      </n-button>
      <n-button
        v-else
        type="primary"
        :loading="schedulerLoading"
        :disabled="schedulerLoading || !businessReady"
        @click="startBusinessOrSelect"
      >
        {{ businessButtonText }}
      </n-button>
      <n-checkbox v-model:checked="autoScrollLog">自动滚动</n-checkbox>
      <n-checkbox v-model:checked="autoSnapshot">预览截图</n-checkbox>
      <div class="action-spacer" />
      <n-button
        size="tiny"
        quaternary
        :loading="snapshotLoading"
        :disabled="snapshotLoading"
        @click="takeSnapshot()"
      >
        手动截图
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import LogTerminal from '@/components/LogTerminal.vue'
import {
  PhonePortraitOutline,
  EyeOutline,
  LayersOutline,
} from '@vicons/ionicons5'
import api, { WS_ORIGIN, debugFileUrl, getErrorMessage } from '@/api'
import { useRuntimeStore } from '@/stores/runtime'
import { getSceneInfo } from '@/utils/scene'

const message = useMessage()
const router = useRouter()
const runtime = useRuntimeStore()
const loading = ref(false)
const schedulerLoading = ref(false)
const snapshotLoading = ref(false)
const snapshot = ref<any>(null)
const autoSnapshot = ref(localStorage.getItem('autoSnapshot') === 'true')
const autoScrollLog = ref(localStorage.getItem('autoScrollLog') !== 'false')
const wsConnected = ref(false)
const wsSnapshotUrl = ref('')
const businessConfig = ref({ buyCity: '', sellCity: '', buyCount: 0, loopCities: [] as string[] })
let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
let wsReconnectDelay = 3000

const stats = computed(() => [
  { label: '运行阶段', value: runtime.tradePhaseText, icon: LayersOutline, color: 'var(--primary)' },
  { label: '当前计数', value: `${runtime.taskCount} 次`, icon: LayersOutline, color: 'var(--text-strong)' },
  { label: '当前位置', value: currentSceneInfo.value.label, icon: EyeOutline, color: 'var(--success)' },
  { label: '日志', value: wsConnected.value ? '在线' : '离线', icon: PhonePortraitOutline, color: wsConnected.value ? 'var(--success)' : 'var(--error)' },
])

const snapshotImageUrl = computed(() => wsSnapshotUrl.value || debugFileUrl(snapshot.value?.screenshot))

const currentSceneInfo = computed(() => getSceneInfo(runtime.scene))

const businessReady = computed(() => Boolean(
  (businessConfig.value.loopCities.length >= 2 || (businessConfig.value.buyCity && businessConfig.value.sellCity))
  && businessConfig.value.buyCount > 0
))

const businessButtonText = computed(() => {
  if (runtime.schedulerRunning) return '运行中'
  return businessReady.value ? '启动任务' : '选择策略'
})

async function refresh() {
  loading.value = true
  await Promise.all([runtime.fetchStatus(), runtime.fetchScene()])
  loading.value = false
}

async function loadBusinessConfig() {
  try {
    const res = await api.config.getCityConfig()
    const runBuy = res.data.RunBuy || {}
    const lc = runBuy.LoopCities
    businessConfig.value = { buyCity: runBuy.BuyCity || '', sellCity: runBuy.SellCity || '', buyCount: Number(runBuy.BuyCount || 0), loopCities: Array.isArray(lc) ? lc : [] }
  } catch {
    message.warning('跑商配置加载失败，请检查后端连接')
    businessConfig.value = { buyCity: '', sellCity: '', buyCount: 0, loopCities: [] }
  }
}

async function startBusinessOrSelect() {
  if (!businessReady.value) { router.push('/business'); return }
  schedulerLoading.value = true
  try {
    const lc = businessConfig.value.loopCities
    const res = lc.length >= 2 ? await api.business.startCities([...lc]) : await api.business.start(businessConfig.value.buyCity, businessConfig.value.sellCity)
    if (res.data.success === false) { message.error(res.data.error || '启动失败'); return }
    message.success('已启动'); await refresh()
  } catch (e) { message.error(getErrorMessage(e, '启动失败'))
  } finally { schedulerLoading.value = false }
}

async function stopScheduler() {
  schedulerLoading.value = true
  try {
    const res = await api.business.stop()
    if (res.data.success === false) { message.error(res.data.error || '停止失败'); return }
    message.success('已停止'); await refresh()
  } catch (e) { message.error(getErrorMessage(e, '停止失败'))
  } finally { schedulerLoading.value = false }
}

async function takeSnapshot(silent = false) {
  if (snapshotLoading.value) return
  snapshotLoading.value = true
  try {
    const res = await api.debug.snapshot([])
    if (res.data.success !== false) { snapshot.value = res.data }
    else if (!silent) message.error(res.data.error || '截图失败')
  } catch (e) { if (!silent) message.error(getErrorMessage(e, '截图失败'))
  } finally { snapshotLoading.value = false }
}

function connectWs() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  try {
    ws = new WebSocket(WS_ORIGIN + '/ws')
  } catch { return scheduleReconnect() }

  ws.onopen = () => {
    wsConnected.value = true
    wsReconnectDelay = 3000
    ws?.send(JSON.stringify({ log: true, sc: true }))
  }

  ws.onmessage = (event) => {
    if (event.data instanceof Blob && autoSnapshot.value) {
      if (wsSnapshotUrl.value) URL.revokeObjectURL(wsSnapshotUrl.value)
      wsSnapshotUrl.value = URL.createObjectURL(event.data)
    } else {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'log') {
          const batch = typeof msg.data === 'string' && msg.data.includes('\n')
          if (!runtime.logTailLoaded) {
            runtime.appendLogPayload(msg.data)
            runtime.logTailLoaded = true
          } else if (!batch) {
            runtime.appendLogPayload(msg.data)
          }
        }
      } catch { /* ignore parse errors */ }
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    ws = null
    scheduleReconnect()
  }

  ws.onerror = () => { ws?.close() }
}

function scheduleReconnect() {
  if (wsReconnectTimer) return
  wsReconnectTimer = setTimeout(() => {
    wsReconnectTimer = null
    wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000)
    connectWs()
  }, wsReconnectDelay)
}

onMounted(() => {
  refresh()
  loadBusinessConfig()
  const timer = setInterval(refresh, 15000)
  connectWs()
  onUnmounted(() => {
    clearInterval(timer)
    if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null }
    if (ws) { ws.onclose = null; ws.close(); ws = null }
    if (wsSnapshotUrl.value) { URL.revokeObjectURL(wsSnapshotUrl.value); wsSnapshotUrl.value = '' }
  })
})

watch(autoSnapshot, v => {
  localStorage.setItem('autoSnapshot', String(v))
  if (!v && wsSnapshotUrl.value) {
    URL.revokeObjectURL(wsSnapshotUrl.value)
    wsSnapshotUrl.value = ''
  }
})
watch(autoScrollLog, v => localStorage.setItem('autoScrollLog', String(v)))
</script>

<style scoped>
.home-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 8px;
  position: relative;
  width: calc(100% - 24px);
  height: calc(100% - 24px);
}

.sc-wrapper {
  width: 100%;
  max-width: 480px;
  aspect-ratio: 16 / 9;
  flex-shrink: 0;
  border-radius: 6px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  background: rgba(0, 0, 0, 0.15);
  border: 1px dashed rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.sc-placeholder {
  color: rgba(255, 255, 255, 0.35);
  font-size: 13px;
}

.sc {
  width: 100%;
  height: 100%;
  border-radius: 6px;
  z-index: 15;
}

.stat-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.top-block {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.stat-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(4px);
  border-radius: 20px;
  font-size: 13px;
}

.stat-chip-label {
  color: var(--text-muted);
  font-weight: 500;
}

.stat-chip-value {
  font-weight: 700;
  color: var(--text-strong);
  margin-left: 2px;
  font-size: 14px;
}

.step-row {
  flex-shrink: 0;
  padding: 6px 16px;
  background: rgba(59, 130, 246, 0.12);
  border-radius: 6px;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
}

.step-arrow {
  color: var(--primary);
  font-weight: bold;
  margin-right: 8px;
}

.step-text {
  color: var(--text-dark);
  font-weight: 500;
}

.log-display {
  flex: 1;
  min-height: 0;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-spacer {
  display: none;
}

.action-container {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  z-index: 15;
}

.action-spacer {
  flex: 1;
}
</style>
