<template>
  <div class="log-terminal-wrapper" @wheel.capture="handleWheel">
    <n-log
      ref="logRef"
      class="n-log-inner"
      :class="{ 'auto-scroll': autoScroll }"
      :log="displayLog"
      :font-size="13"
      :auto-scroll="autoScroll"
      language="resonance"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'

const props = defineProps({
  limit: { type: Number, default: 0 },
  autoScroll: { type: Boolean, default: true },
})

const runtime = useRuntimeStore()
const logRef = ref(null)

function scrollToBottom() {
  ;(logRef.value as any)?.scrollTo({ top: Number.MAX_SAFE_INTEGER })
}

async function keepPinnedToBottom() {
  await nextTick()
  // n-log updates its internal scrollbar after Vue's DOM update. Scheduling one
  // frame later makes every incoming batch stay pinned, not just the toggle.
  requestAnimationFrame(scrollToBottom)
}

function handleWheel(event: WheelEvent) {
  if (!props.autoScroll) return
  event.preventDefault()
  scrollToBottom()
}

watch(() => props.autoScroll, async (enabled) => {
  // Re-enable starts from the newest log line. Disabling leaves the current
  // viewport in place so the user can inspect older lines without a jump.
  if (enabled) {
    await keepPinnedToBottom()
  }
})

const displayLog = computed(() => {
  let content = runtime.logContent
  if (props.limit > 0) {
    const lines = content.split('\n').filter((l: string) => l.trim())
    content = lines.slice(-props.limit).join('\n')
  }
  return content
})

watch(displayLog, () => {
  if (props.autoScroll) {
    void keepPinnedToBottom()
  }
}, { flush: 'post', immediate: true })

defineExpose({
  scrollToBottom,
  clear: () => runtime.clearLog(),
})
</script>

<style scoped>
.log-terminal-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.n-log-inner {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  height: 100%;
}
</style>

<style>
.n-log-inner {
  --n-scrollbar-color: rgba(255, 255, 255, 0.15);
  --n-scrollbar-color-hover: rgba(255, 255, 255, 0.25);
}
.n-log-inner .n-scrollbar-container {
  background: transparent;
  box-sizing: border-box;
  padding: 12px 16px;
}
.n-log-inner .n-scrollbar-content {
  box-sizing: border-box;
  padding-bottom: 8px;
}
.n-log-inner .n-scrollbar-content pre {
  margin: 0;
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.75;
  color: var(--border-lighter);
}
.n-log-inner .n-scrollbar-rail {
  --n-scrollbar-rail-color: transparent;
}

.hljs-time {
  color: var(--text-muted) !important;
  font-weight: normal;
}
.hljs-info {
  color: var(--log-cyan) !important;
  font-weight: bold;
}
.hljs-warning {
  color: var(--log-amber) !important;
  font-weight: bold;
}
.hljs-error {
  color: var(--log-red) !important;
  font-weight: bold;
}
.hljs-built_in {
  color: var(--text-muted) !important;
}
</style>
