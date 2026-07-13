<template>
  <div class="page-container">
    <n-grid :cols="24" :x-gap="20" responsive="screen">
      <n-gi :span="10">
        <n-space vertical :size="20">
          <n-card title="实时识别场景" :segmented="{ content: true }">
            <template #header-extra>
              <n-tag :type="sceneInfo.type" size="small" round>{{ scene || 'UNKNOWN' }}</n-tag>
            </template>
            <div style="text-align: center; padding: 20px 0">
              <div style="font-size: 14px; color: var(--text-muted); margin-bottom: 8px">当前识别结果</div>
              <div style="font-size: 28px; font-weight: 800; color: var(--text-strong)">{{ sceneInfo.label }}</div>
              <div style="font-size: 12px; color: var(--text-faint); margin-top: 12px" v-if="sceneValue !== null">特征值: {{ sceneValue }}</div>
            </div>
          </n-card>

          <n-card title="提取文本摘要" :segmented="{ content: true }">
            <div class="text-tags-container">
              <n-empty v-if="texts.length === 0" description="暂无文本识别数据" size="small" />
              <n-space v-else :size="8">
                <n-tag v-for="t in texts" :key="t" size="small" quaternary round type="primary">{{ t }}</n-tag>
              </n-space>
            </div>
          </n-card>
        </n-space>
      </n-gi>

      <n-gi :span="14">
        <n-card title="OCR 详细数据" :segmented="{ content: true }">
          <template #header-extra>
            <n-button size="tiny" quaternary circle @click="refresh" :loading="loading">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
            </n-button>
          </template>
          <n-data-table
            v-if="ocr.length"
            :columns="ocrColumns"
            :data="ocr"
            size="small"
            :max-height="600"
            :bordered="false"
          />
          <n-empty v-else description="暂无明细数据" style="padding: 100px 0" />
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { NIcon } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import api from '@/api'
import { getSceneInfo } from '@/utils/scene'

const scene = ref<string | null>(null)
const sceneValue = ref<number | null>(null)
const texts = ref<string[]>([])
const ocr = ref<any[]>([])
const loading = ref(false)

const sceneInfo = computed(() => getSceneInfo(scene.value))

const ocrColumns = [
  { title: '识别内容', key: 'text', minWidth: 150 },
  { title: '置信度', key: 'score', width: 90, render: (row: any) => row.score.toFixed(2) },
]

async function refresh() {
  loading.value = true
  try {
    const res = await api.status.scene()
    scene.value = res.data.scene
    sceneValue.value = typeof res.data.value === 'number' ? res.data.value : null
    texts.value = Array.isArray(res.data.text) ? res.data.text : []
    ocr.value = Array.isArray(res.data.ocr) ? res.data.ocr : []
  } catch {}
  loading.value = false
}

onMounted(() => {
  refresh()
  const timer = setInterval(refresh, 3000)
  onUnmounted(() => clearInterval(timer))
})
</script>

<style scoped>
.page-container {
  height: 100%;
  padding: 12px;
  overflow-y: auto;
}

.text-tags-container {
  max-height: 200px;
  overflow-y: auto;
}
</style>
