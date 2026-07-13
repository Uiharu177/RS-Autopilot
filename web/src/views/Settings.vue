<template>
  <div class="page-container">
    <n-space vertical :size="24">
    <n-grid :cols="24" :x-gap="20" responsive="screen">
      <n-gi :span="24">
        <n-card title="自动化偏好" :segmented="{ content: true }" style="flex:1">
          <n-list hoverable clickable>
            <n-list-item>
              <div style="display: flex; align-items: center; justify-content: space-between">
                <div>
                  <div style="font-weight: 600">使用体力药</div>
                  <div style="font-size: 12px; color: var(--text-faint)">体力不足时自动使用提神棒棒糖/口香糖/跳糖</div>
                </div>
                <n-switch v-model:value="configs.use_stamina_item" @update:value="saveGlobalConfig" />
              </div>
            </n-list-item>
            <n-list-item>
              <div style="display: flex; align-items: center; justify-content: space-between">
                <div>
                  <div style="font-weight: 600">疲劳保护</div>
                  <div style="font-size: 12px; color: var(--text-faint)">体力不足时（使用体力药后仍不足）执行的操作</div>
                </div>
                <n-select
                  v-model:value="configs.fatigue_action"
                  :options="[
                    { label: '不启用', value: 'none' },
                    { label: '停在原地', value: 'stay_there' },
                    { label: '返回主界面', value: 'goto_main' },
                    { label: '关闭游戏', value: 'close_game' },
                  ]"
                  @update:value="saveGlobalConfig"
                  style="width: 160px"
                  size="small"
                />
              </div>
            </n-list-item>
            <n-list-item>
              <div style="display: flex; align-items: center; justify-content: space-between">
                <div>
                  <div style="font-weight: 600">停止后动作</div>
                  <div style="font-size: 12px; color: var(--text-faint)">任务停止/完成后对模拟器执行的操作</div>
                </div>
                <n-select
                  v-model:value="configs.on_stop_action"
                  :options="[
                    { label: '停在原地', value: 'stay_there' },
                    { label: '返回主界面', value: 'goto_main' },
                    { label: '关闭游戏', value: 'close_game' },
                  ]"
                  @update:value="saveGlobalConfig"
                  style="width: 160px"
                  size="small"
                />
              </div>
            </n-list-item>
          </n-list>
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api, { getErrorMessage } from '@/api'

const message = useMessage()

const configs = reactive({
  use_stamina_item: false,
  on_stop_action: 'stay_there',
  fatigue_action: 'none',
})

async function loadSettings() {
  try {
    const res = await api.config.get()
    const gc = res.data.config?.global_config || {}
    Object.assign(configs, {
      use_stamina_item: gc.use_stamina_item ?? false,
      on_stop_action: gc.on_stop_action ?? 'stay_there',
      fatigue_action: gc.fatigue_action ?? 'none',
    })
  } catch {}
}

async function saveGlobalConfig() {
  try {
    await api.config.save({ global_config: { ...configs } })
    message.success('偏好设置已保存')
  } catch (e) {
    message.error(getErrorMessage(e, '保存失败'))
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.page-container {
  height: 100%;
  padding: 12px;
  overflow-y: auto;
}
</style>
