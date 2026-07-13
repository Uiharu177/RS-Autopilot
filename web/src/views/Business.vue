<template>
  <div class="page-container">
    <n-grid :cols="24" :x-gap="20" responsive="screen" style="height: 100%">
      <!-- 左侧：路线配置 -->
      <n-gi :span="14" style="height: 100%; display: flex; flex-direction: column">
        <n-card title="路线编排" :segmented="{ content: true }" class="full-height-card">
          <template #header-extra>
            <n-tag type="info" size="small" round ghost v-if="routeCities.length >= 2">
              共 {{ routeCities.length }} 站
            </n-tag>
          </template>
          
          <div style="display: flex; flex-direction: column; height: 100%; gap: 20px">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; color: var(--text-muted); font-weight: 600">可选城市</span>
              <n-a href="https://www.resonance-columba.com/route" target="_blank" style="font-size: 12px">科伦巴商会</n-a>
            </div>
              <n-input v-model:value="citySearch" placeholder="搜索城市..." size="small" clearable style="margin-bottom: 8px" />
              <n-space style="flex-wrap: wrap">
                <n-tag
                  v-for="city in availableCities"
                  :key="city"
                  :bordered="false"
                  :type="routeCities.includes(city) ? 'success' : 'default'"
                  style="cursor: pointer; transition: all 0.2s"
                  @click="addCity(city)"
                >
                  <template #icon>
                    <n-icon v-if="routeCities.includes(city)"><CheckmarkOutline /></n-icon>
                    <n-icon v-else><AddOutline /></n-icon>
                  </template>
                  {{ city }}
                </n-tag>
              </n-space>
            </div>

            <n-divider dashed style="margin: 0" />

            <div style="flex: 1; min-height: 0; display: flex; flex-direction: column">
              <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px; font-weight: 600">路线顺序</div>
              <div class="route-list-container">
                <div v-if="routeCities.length > 0" class="route-list">
                  <div v-for="(city, idx) in routeCities" :key="`${city}-${idx}`" class="route-node">
                    <div class="route-node__index">{{ idx + 1 }}</div>
                    <div class="route-node__content">
                      <span style="font-weight: 600; color: var(--text-strong)">{{ city }}</span>
                    </div>
                    <n-button-group size="tiny" quaternary>
                      <n-button :disabled="idx === 0" circle @click="moveUp(idx)">
                        <template #icon><n-icon><ChevronUpOutline /></n-icon></template>
                      </n-button>
                      <n-button :disabled="idx === routeCities.length - 1" circle @click="moveDown(idx)">
                        <template #icon><n-icon><ChevronDownOutline /></n-icon></template>
                      </n-button>
                      <n-button type="error" circle @click="removeCity(idx)">
                        <template #icon><n-icon><CloseOutline /></n-icon></template>
                      </n-button>
                    </n-button-group>
                  </div>
                  <!-- 循环指示 -->
                  <div v-if="routeCities.length >= 2" class="route-loop-indicator">
                    <n-icon size="14" style="margin-right: 4px"><RefreshOutline /></n-icon>
                    回到 {{ routeCities[0] }} 开始下一圈
                  </div>
                </div>
                <n-empty v-else description="点击上方城市开始规划路线" style="padding: 40px 0" />
              </div>
            </div>
          </div>
        </n-card>
      </n-gi>

      <!-- 右侧：详细参数 -->
      <n-gi :span="10" style="height: 100%; display: flex; flex-direction: column">
        <n-space vertical :size="20" style="height: 100%">
          <n-card title="运行配置" class="full-height-card" :segmented="{ content: true, footer: true }">
            <n-form-item label="计划运行圈数" feedback="每跑完一次完整的路线序列记为一圈">
              <n-input-number
                v-model:value="buyCount"
                :min="1"
                :max="99"
                style="width: 100%"
                placeholder="请输入圈数"
              >
                <template #suffix>圈</template>
              </n-input-number>
            </n-form-item>

            <n-tabs type="segment" animated size="small">
              <n-tab-pane name="book" tab="进货书数量">
                <div class="config-grid">
                  <div v-for="city in allCities" :key="'book-'+city" class="config-item">
                    <span class="config-item__label">{{ city }}</span>
                    <n-input-number v-model:value="bookSettings[city]" :min="0" size="small" style="width: 100%" />
                  </div>
                </div>
              </n-tab-pane>
              <n-tab-pane name="haggle" tab="议价等级">
                <div class="config-grid">
                  <div v-for="city in allCities" :key="'haggle-'+city" class="config-item">
                    <span class="config-item__label">{{ city }}</span>
                    <n-input-number v-model:value="haggleSettings[city]" :min="0" size="small" style="width: 100%" />
                  </div>
                </div>
              </n-tab-pane>
            </n-tabs>

            <template #footer>
              <n-space vertical :size="12">
                <n-space align="center" justify="space-between">
                  <n-button type="primary" size="large" @click="startRun" :loading="running" style="flex: 1">
                    <template #icon><n-icon><IconPlay /></n-icon></template>
                    启动跑商任务
                  </n-button>
                  <n-tag v-if="saveStatus === 'saving'" type="warning" size="small" round>保存中</n-tag>
                  <n-tag v-else-if="saveStatus === 'unsaved'" type="error" size="small" round>未保存</n-tag>
                  <n-tag v-else type="success" size="small" round>已保存</n-tag>
                </n-space>
                <n-grid :cols="2" :x-gap="12">
                  <n-gi>
                    <n-button block secondary @click="startPageFlow" :loading="pageFlowLoading">验证流程</n-button>
                  </n-gi>
                  <n-gi>
                    <n-button block secondary type="error" @click="stopRun" :disabled="!running && !pageFlowLoading">停止</n-button>
                  </n-gi>
                </n-grid>
              </n-space>
            </template>
          </n-card>

          <n-alert type="warning" size="small" :show-icon="false">
            <div style="font-size: 12px; line-height: 1.6">
              <b>提示:</b> 启动前请确保模拟器处于游戏主界面或车站界面。环线模式下，任务将按顺序依次访问列表中所有城市。
            </div>
          </n-alert>
        </n-space>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { onBeforeRouteLeave } from 'vue-router'
import {
  Play as IconPlay, AddOutline, ChevronUpOutline, ChevronDownOutline,
  CloseOutline, CheckmarkOutline, RefreshOutline
} from '@vicons/ionicons5'
import api, { getErrorMessage } from '@/api'

const message = useMessage()
const dialog = useDialog()

const allCities = ref<string[]>([])
const routeCities = ref<string[]>([])
const citySearch = ref('')
const buyCount = ref(3)
const running = ref(false)
const pageFlowLoading = ref(false)

const bookSettings = reactive<Record<string, number>>({})
const haggleSettings = reactive<Record<string, number>>({})
const loaded = ref(false)
const saveStatus = ref<'saved' | 'saving' | 'unsaved'>('saved')
let saveTimer: ReturnType<typeof setTimeout> | null = null
let pendingSave: Promise<boolean> | null = null
let runningCheckTimer: ReturnType<typeof setInterval> | null = null

function stopRunningCheck() {
  if (runningCheckTimer) {
    clearInterval(runningCheckTimer)
    runningCheckTimer = null
  }
}

watch(running, (val) => {
  if (val) {
    runningCheckTimer = setInterval(async () => {
      try {
        const res = await api.scheduler.status()
        const schedRunning = !!(res.data.running ?? res.data.scheduler_running)
        if (!schedRunning) running.value = false
      } catch {}
    }, 3000)
  } else {
    stopRunningCheck()
  }
})

async function autoSave() {
  saveStatus.value = 'saving'
  pendingSave = saveConfig(false)
  const ok = await pendingSave
  pendingSave = null
  saveStatus.value = ok ? 'saved' : 'unsaved'
}

watch([routeCities, buyCount, haggleSettings, bookSettings], () => {
  if (!loaded.value) return
  saveStatus.value = 'unsaved'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(autoSave, 600)
})

onBeforeRouteLeave(async () => {
  if (saveTimer) clearTimeout(saveTimer)
  if (pendingSave) {
    await pendingSave
  } else if (saveStatus.value !== 'saved') {
    await saveConfig(false)
  }
})

const availableCities = computed(() => {
  const kw = citySearch.value.trim().toLowerCase()
  if (!kw) return allCities.value
  return allCities.value.filter(c => c.toLowerCase().includes(kw))
})

const previewCities = computed(() => {
  if (routeCities.value.length < 2) return routeCities.value
  return [...routeCities.value, routeCities.value[0]]
})

function addCity(city: string) {
  if (!routeCities.value.includes(city)) {
    routeCities.value = [...routeCities.value, city]
  }
}

function removeCity(idx: number) {
  routeCities.value = routeCities.value.filter((_, i) => i !== idx)
}

function moveUp(idx: number) {
  if (idx <= 0) return
  const arr = [...routeCities.value]
  arr[idx] = arr[idx - 1]
  arr[idx - 1] = routeCities.value[idx]
  routeCities.value = arr
}

function moveDown(idx: number) {
  if (idx >= routeCities.value.length - 1) return
  const arr = [...routeCities.value]
  arr[idx] = arr[idx + 1]
  arr[idx + 1] = routeCities.value[idx]
  routeCities.value = arr
}

async function loadCities() {
  try {
    const res = await api.business.cities()
    allCities.value = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.cities) ? res.data.cities : [])
    for (const city of allCities.value) {
      if (bookSettings[city] === undefined) bookSettings[city] = 0
      if (haggleSettings[city] === undefined) haggleSettings[city] = 0
    }
  } catch (e) {
    message.error(getErrorMessage(e, '加载城市列表失败'))
  }
}

async function loadConfig() {
  try {
    const res = await api.config.getCityConfig()
    const data = res.data
    const runBuy = data.RunBuy || {}

    buyCount.value = runBuy.BuyCount ?? 0

    const loop = runBuy.LoopCities
    if (Array.isArray(loop) && loop.length >= 2) {
      routeCities.value = [...loop]
    } else if (runBuy.BuyCity && runBuy.SellCity) {
      routeCities.value = [runBuy.BuyCity, runBuy.SellCity]
    }

    for (const city of allCities.value) {
      if (data.CityBook && data.CityBook[city] !== undefined) {
        bookSettings[city] = data.CityBook[city]
      }
      if (data.CityHaggle && data.CityHaggle[city] !== undefined) {
        haggleSettings[city] = data.CityHaggle[city]
      }
    }
  } catch {}
}

async function saveConfig(showError = true) {
  try {
    await api.config.saveCityConfig({
      CityBook: { ...bookSettings },
      CityHaggle: { ...haggleSettings },
      RunBuy: {
        BuyCount: buyCount.value,
        LoopCities: [...routeCities.value],
      },
    })
    return true
  } catch (e) {
    if (showError) message.error(getErrorMessage(e, '保存跑商配置失败'))
    return false
  }
}

async function startRun() {
  if (routeCities.value.length < 2) {
    message.warning('请至少选择 2 个城市组成路线')
    return
  }
  if (!buyCount.value || buyCount.value <= 0) {
    message.warning('请设置大于 0 的运行圈数')
    return
  }
  if (!await saveConfig()) return

  const preview = previewCities.value.join(' → ')
  dialog.info({
    title: '确认',
    content: `环线跑商: ${preview}\n运行圈数: ${buyCount.value}`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      running.value = true
      try {
        const res = await api.business.startCities([...routeCities.value])
        if (res.data.success !== false) {
          message.success('跑商任务已启动')
        } else {
          message.error('启动失败: ' + (res.data.error || ''))
          running.value = false
        }
      } catch (e) {
        message.error(getErrorMessage(e, '启动失败'))
        running.value = false
      }
    },
  })
}

async function stopRun() {
  dialog.warning({
    title: '确认停止',
    content: '确定要停止当前任务吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.business.stop()
        if (res.data.success === false) {
          message.error(res.data.error || '停止失败')
        } else {
          message.success('已停止')
        }
      } catch (e) {
        message.error(getErrorMessage(e, '停止失败'))
      }
      running.value = false
      pageFlowLoading.value = false
    },
  })
}

async function startPageFlow() {
  if (routeCities.value.length < 2) {
    message.warning('请至少选择 2 个城市进行测试')
    return
  }
  if (!await saveConfig()) return
  pageFlowLoading.value = true
  try {
    message.info('正在验证页面切换流程，请观察日志...')
    const res = await api.debug.tradePageFlowCities([...routeCities.value], 1)
    if (res.data.success) {
      message.success('页面流程验证完成')
    } else {
      message.error('验证失败: ' + (res.data.error || ''))
    }
  } catch (e) {
    message.error(getErrorMessage(e, '请求测试流程失败'))
  } finally {
    pageFlowLoading.value = false
  }
}

onMounted(async () => {
  await loadCities()
  await loadConfig()
  loaded.value = true
})

onUnmounted(() => {
  stopRunningCheck()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  padding: 12px;
  overflow-y: auto;
}

.full-height-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.full-height-card > .n-card__content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.route-list-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.route-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.route-node {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(248, 250, 252, 0.5);
  border: 1px solid var(--border-lighter);
  border-radius: 8px;
  transition: all 0.2s;
}

.route-node:hover {
  border-color: var(--primary);
  background: var(--bg-blue-light);
}

.route-node__index {
  width: 22px;
  height: 22px;
  background: var(--primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.route-node__content {
  flex: 1;
}

.route-loop-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  font-size: 12px;
  color: var(--text-faint);
  font-weight: 500;
  background: var(--bg-light);
  border-radius: 6px;
  margin-top: 4px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  padding: 8px 0;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item__label {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
