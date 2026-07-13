<template>
  <div class="debug-layout">
    <div class="debug-sidebar">
      <div class="debug-sidebar-header">
        <span class="debug-sidebar-title">日志文件</span>
        <n-button size="tiny" quaternary circle @click="loadLogFiles">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
        </n-button>
      </div>
      <n-list hoverable clickable bordered class="debug-file-list">
        <n-list-item
          v-for="f in logFiles"
          :key="f.name"
          :class="{ active: selectedFile === f.name }"
          @click="selectFile(f)"
        >
          <div class="debug-file-item">
            <n-icon size="16" color="var(--text-faint)"><DocumentOutline /></n-icon>
            <div class="debug-file-info">
              <div class="debug-file-name">{{ f.name }}</div>
              <div class="debug-file-meta">{{ (f.size / 1024).toFixed(1) }} KB</div>
            </div>
          </div>
        </n-list-item>
      </n-list>
      <n-empty v-if="!logFiles.length" description="暂无日志文件" size="small" style="padding: 24px" />
    </div>

    <div class="debug-main" v-if="selectedFile">
      <div class="debug-main-header">
        <span class="debug-main-title">{{ selectedFile }}</span>
        <n-space>
          <n-tag size="small" type="info" ghost>{{ segments.length }} 个节点</n-tag>
          <n-tag size="small" v-if="currentScreenshot" type="success" ghost>有截图</n-tag>
        </n-space>
      </div>

      <div class="debug-main-body" v-if="segments.length">
        <div class="debug-screenshot">
          <n-image
            v-if="currentScreenshot"
            :src="screenshotUrl(currentScreenshot)"
            width="100%"
            object-fit="contain"
            preview-disabled
            class="debug-screenshot-img"
          />
          <div v-else class="debug-screenshot-empty">
            <n-icon size="48" color="var(--text-muted)"><ImageOutline /></n-icon>
            <span>该节点无截图</span>
          </div>
          <div class="debug-screenshot-time" v-if="currentTime">
            <n-tag size="small" round>{{ currentTime }}</n-tag>
          </div>
        </div>

        <div class="debug-timeline">
          <div class="debug-timeline-bar">
            <n-button size="tiny" quaternary :disabled="currentIndex <= 0" @click="prevSegment">
              <template #icon><n-icon><ChevronBackOutline /></n-icon></template>
            </n-button>
            <n-slider
              :value="sliderValue"
              @update:value="onSliderInput"
              :min="0"
              :max="Math.max(0, segments.length - 1)"
              :step="1"
              class="debug-timeline-slider"
            />
            <n-button size="tiny" quaternary :disabled="currentIndex >= segments.length - 1" @click="nextSegment">
              <template #icon><n-icon><ChevronForwardOutline /></n-icon></template>
            </n-button>
            <span class="debug-timeline-pos">{{ currentIndex + 1 }} / {{ segments.length }}</span>
          </div>
          <div class="debug-log" ref="logEl">
            <pre class="debug-log-text">{{ currentLogLines.join('\n') }}</pre>
          </div>
        </div>
      </div>

      <div class="debug-main-empty" v-else-if="!loading">
        <n-empty description="该日志文件没有截图节点" size="medium" />
      </div>
    </div>

    <div class="debug-main debug-main--empty" v-else>
      <n-empty description="从左侧选择日志文件" size="large">
        <template #extra>
          <n-icon size="64" color="var(--text-light)"><DocumentOutline /></n-icon>
        </template>
      </n-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { NIcon } from 'naive-ui'
import {
  RefreshOutline, DocumentOutline, ImageOutline,
  ChevronBackOutline, ChevronForwardOutline,
} from '@vicons/ionicons5'
import api from '@/api'

const logFiles = ref<any[]>([])
const selectedFile = ref('')
const segments = ref<{ time: string; log_lines: string[]; screenshot: string | null }[]>([])
const currentIndex = ref(0)
const sliderValue = ref(0)
const loading = ref(false)
const logEl = ref<HTMLElement | null>(null)

const currentSegment = computed(() => segments.value[currentIndex.value] || null)
const currentScreenshot = computed(() => currentSegment.value?.screenshot || null)
const currentTime = computed(() => currentSegment.value?.time || '')
const currentLogLines = computed(() => currentSegment.value?.log_lines || [])

function screenshotUrl(name: string) {
  return api.debug.screenshotUrl(name)
}

async function loadLogFiles() {
  try {
    const res = await api.debug.logs()
    if (res.data.success !== false) {
      logFiles.value = res.data.logs || []
    }
  } catch {}
}

async function selectFile(f: any) {
  selectedFile.value = f.name
  segments.value = []
  currentIndex.value = 0
  sliderValue.value = 0
  loading.value = true
  try {
    const res = await api.debug.timeline(f.name)
    if (res.data.success !== false) {
      segments.value = res.data.segments || []
    }
  } catch {}
  loading.value = false
}

function prevSegment() {
  if (currentIndex.value > 0) currentIndex.value--
}

function nextSegment() {
  if (currentIndex.value < segments.value.length - 1) currentIndex.value++
}

let sliderTimer: ReturnType<typeof setTimeout> | null = null
function onSliderInput(v: number) {
  sliderValue.value = v
  if (sliderTimer) clearTimeout(sliderTimer)
  sliderTimer = setTimeout(() => {
    currentIndex.value = v
  }, 150)
}

watch(currentIndex, (v) => {
  sliderValue.value = v
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = 0
  })
})

onMounted(() => {
  loadLogFiles()
})
</script>

<style scoped>
.debug-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.debug-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.6);
}

.debug-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.debug-main--empty {
  align-items: center;
  justify-content: center;
}

.debug-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  flex-shrink: 0;
}

.debug-sidebar-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-strong);
}

.debug-file-list {
  flex: 1;
  overflow-y: auto;
  border: none;
}

.debug-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.debug-file-info {
  flex: 1;
  min-width: 0;
}

.debug-file-name {
  font-size: 13px;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.debug-file-meta {
  font-size: 11px;
  color: var(--text-faint);
}

.debug-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-light);
}

.debug-main-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-strong);
}

.debug-main-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.debug-main-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.debug-screenshot {
  height: 45%;
  flex-shrink: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-dark);
  border-bottom: 1px solid var(--border-dark);
}

.debug-screenshot-img {
  max-height: 100%;
  object-fit: contain;
}

.debug-screenshot-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.debug-screenshot-time {
  position: absolute;
  top: 8px;
  right: 8px;
}

.debug-timeline {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.debug-timeline-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--bg-light);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.debug-timeline-slider {
  flex: 1;
}

.debug-timeline-pos {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  min-width: 60px;
  text-align: right;
}

.debug-log {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-dark);
  padding: 12px 16px;
}

.debug-log-text {
  margin: 0;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-light);
  white-space: pre-wrap;
  word-break: break-all;
}

:deep(.n-list-item.active) {
  background: var(--bg-blue-light) !important;
}

:deep(.n-list-item.active .debug-file-name) {
  color: var(--primary-hover);
  font-weight: 600;
}
</style>
