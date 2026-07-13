<template>
  <div class="log-terminal-wrapper">
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
import { computed, ref, watch } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'

const props = defineProps({
  limit: { type: Number, default: 0 },
  autoScroll: { type: Boolean, default: true },
})

const runtime = useRuntimeStore()
const logRef = ref(null)

watch(() => props.autoScroll, (val) => {
  if (!val) {
    setTimeout(() => (logRef.value as any)?.scrollTo({ top: 99999 }), 0)
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

defineExpose({
  scrollToBottom: () => (logRef.value as any)?.scrollTo({ top: 99999 }),
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
  padding: 12px 16px 0;
}
.n-log-inner .n-scrollbar-content {
  padding-bottom: 4px;
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

.n-log-inner.auto-scroll .n-scrollbar-container {
  overflow: hidden;
  position: relative;
  padding: 12px 16px 0;
}
.n-log-inner.auto-scroll .n-scrollbar-container .n-scrollbar-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding-bottom: 4px;
}
.n-log-inner.auto-scroll .n-scrollbar-rail {
  display: none;
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
