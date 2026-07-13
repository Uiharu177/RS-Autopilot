<template>
  <div class="page-container">
  <n-space vertical :size="20">
    <n-h2>调度器管理</n-h2>

    <n-card title="控制">
      <n-space align="center">
        <n-tag :type="running ? 'success' : 'default'" size="large">
          {{ running ? '运行中' : '已停止' }}
        </n-tag>
        <n-tag size="large">任务数: {{ taskCount }}</n-tag>
      </n-space>
      <n-space style="margin-top: 12px">
        <n-button type="primary" @click="startScheduler" :loading="loading" :disabled="running">
          <template #icon><n-icon><IconPlay /></n-icon></template>
          启动
        </n-button>
        <n-button type="error" @click="stopScheduler" :loading="loading" :disabled="!running">
          <template #icon><n-icon><IconClose /></n-icon></template>
          停止
        </n-button>
      </n-space>
    </n-card>

    <n-card title="定时任务">
      <template #header-extra>
        <n-button type="primary" size="small" @click="showAddModal = true">
          <template #icon><n-icon><IconAdd /></n-icon></template>
          添加任务
        </n-button>
      </template>
      <n-empty v-if="tasks.length === 0" description="暂无任务" />
      <n-table v-else>
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>状态</th>
            <th>下次运行</th>
            <th>运行次数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.name">
            <td>{{ task.name }}</td>
            <td><n-tag size="small">{{ task.task_type }}</n-tag></td>
            <td>
              <n-tag :type="statusColor(task.status)" size="small">{{ task.status }}</n-tag>
            </td>
            <td>{{ task.next_run || '-' }}</td>
            <td>{{ task.run_count }}</td>
            <td>
              <n-space>
                <n-button size="tiny" @click="removeTask(task)" type="error">删除</n-button>
              </n-space>
            </td>
          </tr>
        </tbody>
      </n-table>
    </n-card>

    <n-modal v-model:show="showAddModal" title="添加定时任务">
      <n-card style="width: 500px">
        <n-form :model="formData" label-placement="left" label-width="100px">
          <n-form-item label="名称">
            <n-input v-model:value="formData.name" placeholder="任务名称" />
          </n-form-item>
          <n-form-item label="类型">
            <n-select v-model:value="formData.task_type" :options="taskTypeOptions" />
          </n-form-item>
          <n-form-item v-if="formData.task_type === 'daily'" label="每日时间">
            <n-time-picker v-model:value="formData.dailyTime" format="HH:mm" />
          </n-form-item>
          <n-form-item v-if="formData.task_type === 'periodic'" label="间隔(分)">
            <n-input-number v-model:value="formData.interval" :min="1" />
          </n-form-item>
          <n-form-item>
            <n-space>
              <n-button type="primary" @click="addTask">添加</n-button>
              <n-button @click="showAddModal = false">取消</n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>
    </n-modal>
  </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Play as IconPlay, Add as IconAdd, Close as IconClose } from '@vicons/ionicons5'
import { NIcon, useMessage } from 'naive-ui'
import api from '@/api'

const message = useMessage()
const running = ref(false)
const taskCount = ref(0)
const loading = ref(false)
const tasks = ref<any[]>([])
const showAddModal = ref(false)

const formData = ref({
  name: '',
  task_type: 'daily',
  dailyTime: 0,
  interval: 60,
})

const taskTypeOptions = [
  { label: '每日', value: 'daily' },
  { label: '周期性', value: 'periodic' },
]

function statusColor(status: string) {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default' | 'info'> = {
    running: 'success',
    completed: 'default',
    failed: 'error',
    pending: 'info',
    cancelled: 'warning',
  }
  return map[status] || 'default'
}

async function fetchStatus() {
  try {
    const res = await api.scheduler.status()
    running.value = res.data.running
    taskCount.value = res.data.task_count
    if (res.data.tasks) tasks.value = res.data.tasks
  } catch {}
}

async function startScheduler() {
  loading.value = true
  try {
    await api.scheduler.start()
    message.success('调度器已启动')
    await fetchStatus()
  } catch {
    message.error('启动失败')
  } finally {
    loading.value = false
  }
}

async function stopScheduler() {
  loading.value = true
  try {
    await api.scheduler.stop()
    message.success('调度器已停止')
    await fetchStatus()
  } catch {
    message.error('停止失败')
  } finally {
    loading.value = false
  }
}

function addTask() {
  message.info('请通过跑商页面添加任务')
  showAddModal.value = false
}

async function removeTask(_task: any) {
  try {
    await api.business.stop()
    message.success('已删除任务')
    await fetchStatus()
  } catch {
    message.error('删除失败')
  }
}

onMounted(fetchStatus)
</script>

<style scoped>
.page-container {
  height: 100%;
  padding: 12px;
  overflow-y: auto;
}
</style>
