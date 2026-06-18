import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

function asBool(value: unknown) {
  return value === true || value === 'true' || value === 1
}

function normalizeLogLines(payload: unknown) {
  const data = payload as any
  if (typeof data === 'string') return data.split(/\r?\n/).filter(Boolean)
  if (Array.isArray(data)) return data.map(String).filter(Boolean)
  if (Array.isArray(data?.lines)) return data.lines.map(String).filter(Boolean)
  if (Array.isArray(data?.logs)) return data.logs.map(String).filter(Boolean)
  const message = data?.message ?? data?.line ?? data?.log ?? data?.text
  return typeof message === 'string' && message ? [message] : []
}

function inferTradePhase(message: string) {
  if (message.includes('收益归位')) return 'normalizing'
  if (message.includes('正式巡航') || message.includes('端点跑商完成') || /开始第 \d+\/\d+ 轮端点跑商/.test(message)) return 'cruising'
  if (message.includes('页面流程')) return 'page-flow'
  return null
}

function extractLogMessage(line: string) {
  const match = line.match(/^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\w+\s+(.*)$/)
  if (match?.[1]) return match[1].trim()
  return line.split(' -  ').pop()?.trim() || line.trim()
}

function latestSessionLines(lines: string[]) {
  let startIndex = -1
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].includes('启动时间:')) {
      startIndex = i
      break
    }
  }
  if (startIndex === -1) return lines
  return lines.slice(startIndex)
}

export const useRuntimeStore = defineStore('runtime', () => {
  const connected = ref(false)
  const schedulerRunning = ref(false)
  const taskCount = ref(0)
  const scene = ref<string | null>(null)
  const sceneOcr = ref<any[]>([])
  const sceneText = ref<string[]>([])
  const logLines = ref<string[]>([])
  const logContent = ref('')
  const logTailLoaded = ref(false)
  const currentStep = ref('等待任务')
  const tradePhase = ref<'idle' | 'normalizing' | 'cruising' | 'page-flow' | 'unknown'>('idle')

  const tradePhaseText = computed(() => {
    if (tradePhase.value === 'normalizing') return '收益归位'
    if (tradePhase.value === 'cruising') return '正式巡航'
    if (tradePhase.value === 'page-flow') return '页面流程验证'
    if (tradePhase.value === 'unknown') return '未知阶段'
    return '等待任务'
  })

  const statusText = computed(() => {
    if (!connected.value) return '未连接'
    if (schedulerRunning.value) return '运行中'
    return '已就绪'
  })

  const statusType = computed<'success' | 'warning' | 'error' | 'default'>(() => {
    if (!connected.value) return 'error'
    if (schedulerRunning.value) return 'success'
    return 'warning'
  })

  async function fetchStatus() {
    try {
      const [dev, sched] = await Promise.all([
        api.device.status(),
        api.scheduler.status(),
      ])
      connected.value = asBool(dev.data.connected ?? dev.data.success)
      schedulerRunning.value = asBool(sched.data.running ?? sched.data.scheduler_running)
      taskCount.value = Number(sched.data.task_count ?? sched.data.taskCount ?? sched.data.tasks?.length ?? 0)
    } catch {}
  }

  async function fetchScene() {
    try {
      const res = await api.status.scene()
      scene.value = res.data.scene?.name ?? res.data.scene ?? res.data.name ?? null
      sceneOcr.value = res.data.ocr ?? []
      sceneText.value = Array.isArray(res.data.text) ? res.data.text : []
    } catch {}
  }

  const MAX_LOG_LINES = 200

  function appendLog(line: string) {
    if (!line) return
    if (line.includes('[SC]')) return
    logLines.value.push(line)
    if (logLines.value.length > MAX_LOG_LINES) {
      logLines.value = logLines.value.slice(-MAX_LOG_LINES)
    }
    logContent.value = logLines.value.join('\n') + '\n'
    const message = extractLogMessage(line)
    if (message && !message.startsWith('[')) {
      currentStep.value = message
      const phase = inferTradePhase(message)
      if (phase) tradePhase.value = phase
    }
  }

  function appendLogPayload(payload: unknown) {
    const data = payload as any
    const rawLines = normalizeLogLines(payload)
    const lines = Array.isArray(data?.lines) ? latestSessionLines(rawLines) : rawLines
    for (const line of lines) appendLog(line)
    return lines.length
  }

  function clearLog() {
    logLines.value = []
    logContent.value = ''
    logTailLoaded.value = true
    currentStep.value = '等待任务'
    tradePhase.value = 'idle'
  }

  return {
    connected,
    schedulerRunning,
    taskCount,
    scene,
    sceneOcr,
    sceneText,
    logLines,
    logContent,
    logTailLoaded,
    currentStep,
    tradePhase,
    tradePhaseText,
    statusText,
    statusType,
    fetchStatus,
    fetchScene,
    appendLog,
    appendLogPayload,
    clearLog,
  }
})
