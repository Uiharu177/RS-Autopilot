<template>
  <n-space vertical :size="20">

    <n-card title="连接设置">
      <n-form label-placement="left" label-width="140px">
        <n-form-item label="ADB端口">
          <n-input-number
            v-model:value="port"
            :min="1"
            :max="65535"
            placeholder="16384"
            style="width: 200px"
          >
            <template #prefix>127.0.0.1:</template>
          </n-input-number>
        </n-form-item>

        <n-form-item label="触控方式">
          <n-select
            v-model:value="touchMethod"
            :options="touchOptions"
            style="width: 240px"
            @update:value="saveSettings"
          />
        </n-form-item>

        <n-form-item label="截图方式">
          <n-select
            v-model:value="screenshotMethod"
            :options="screenshotOptions"
            style="width: 240px"
            @update:value="saveSettings"
          />
          <n-text v-if="actualMethod" depth="3" style="margin-top: 4px; display: block; font-size: 12px;">
            当前实际: {{ actualMethod.toUpperCase() }}
          </n-text>
        </n-form-item>

        <n-form-item>
          <n-space>
            <n-button type="primary" @click="connectDevice" :loading="connecting">
              连接
            </n-button>
            <n-button @click="autoSelectScreenshot" :loading="benchmarking">
              测速并自动选择截图
            </n-button>
            <n-button @click="disconnect">断开</n-button>
          </n-space>
        </n-form-item>

        <n-form-item label="游戏控制">
          <n-space>
            <n-button @click="startGame" :loading="gameLoading" type="success" ghost>
              启动游戏
            </n-button>
            <n-button @click="stopGame" :loading="gameLoading" type="warning" ghost>
              关闭游戏
            </n-button>
            <n-button @click="restartGame" :loading="gameLoading" type="info" ghost>
              重启游戏
            </n-button>
          </n-space>
        </n-form-item>
      </n-form>

      <n-alert v-if="statusMessage" :type="statusType" :title="statusMessage" closable @close="statusMessage = ''" />

      <n-card v-if="benchmarkResult" size="small" title="截图测速结果" style="margin-top: 12px">
        <n-space vertical>
          <n-tag :type="benchmarkResult.fastest ? 'success' : 'error'">
            最快截图方式: {{ benchmarkResult.fastest || '无可用方式' }}
          </n-tag>
          <n-table size="small">
            <thead>
              <tr><th>方式</th><th>状态</th><th>平均</th><th>最小</th><th>最大</th><th>错误</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in benchmarkResult.results || []" :key="item.method">
                <td>{{ item.method }}</td>
                <td><n-tag size="small" :type="item.ok ? 'success' : 'error'">{{ item.ok ? '可用' : '不可用' }}</n-tag></td>
                <td>{{ item.avg_ms ?? '-' }} ms</td>
                <td>{{ item.min_ms ?? '-' }} ms</td>
                <td>{{ item.max_ms ?? '-' }} ms</td>
                <td>{{ item.error || '-' }}</td>
              </tr>
            </tbody>
          </n-table>
        </n-space>
      </n-card>
    </n-card>

    <n-card title="模拟器扫描">
      <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
        首次使用请先扫描，检测到模拟器后点击「使用此设备」将自动填入端口和模拟器信息。
      </n-alert>
      <n-space>
        <n-button @click="scan" :loading="scanning">扫描</n-button>
      </n-space>
      <n-table v-if="devices.length > 0" style="margin-top: 12px">
        <thead>
          <tr><th>名称</th><th>端口</th><th>类型</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="dev in devices" :key="dev.port">
            <td>{{ dev.name }}</td>
            <td>127.0.0.1:{{ dev.port }}</td>
            <td>{{ dev.type }}</td>
            <td>
              <n-button size="small" @click="applyDevice(dev)">使用此设备</n-button>
            </td>
          </tr>
        </tbody>
      </n-table>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api, { getErrorMessage } from '@/api'

const message = useMessage()

const port = ref(16384)
const devicePath = ref('')
const deviceType = ref('')
const touchMethod = ref('adb')
const screenshotMethod = ref('adb')

const touchOptions = [
  { label: 'ADB (通用)', value: 'adb' },
  { label: 'NEMU (MuMu IPC)', value: 'nemu' },
  { label: 'Scrcpy', value: 'scrcpy' },
]

const screenshotOptions = [
  { label: 'ADB screencap (通用)', value: 'adb' },
  { label: 'NEMU (MuMu IPC)', value: 'nemu' },
  { label: 'DroidCast', value: 'droidcast' },
  { label: 'Scrcpy', value: 'scrcpy' },
]

const connecting = ref(false)
const benchmarking = ref(false)
const scanning = ref(false)
const gameLoading = ref(false)
const devices = ref<any[]>([])
const benchmarkResult = ref<any>(null)
const statusMessage = ref('')
const statusType = ref<'success' | 'error' | 'warning'>('success')
const actualMethod = ref('')

async function loadSettings() {
  try {
    const res = await api.config.get()
    const g = res.data.app?.Global || {}
    const dev = g.device || {}
    port.value = dev.port ?? 16384
    devicePath.value = dev.path || ''
    deviceType.value = dev.type || ''
    touchMethod.value = g.touch_method || 'adb'
    screenshotMethod.value = g.screenshot_method || 'adb'
  } catch {}
  refreshDeviceStatus()
}

async function refreshDeviceStatus() {
  try {
    const res = await api.device.status()
    actualMethod.value = res.data.actual_method || ''
  } catch {}
}

async function saveSettings() {
  try {
    await api.config.save({
      port: port.value,
      device_path: devicePath.value,
      device_type: deviceType.value,
      touch_method: touchMethod.value,
      screenshot_method: screenshotMethod.value,
    })
  } catch {}
}

async function connectDevice() {
  connecting.value = true
  statusMessage.value = ''
  await saveSettings()
  try {
    const res = await api.device.connect(port.value)
    const actualMethod = res.data.actual_method || res.data.actualMethod || res.data.method || screenshotMethod.value
    if (res.data.success !== false) {
      if (res.data.fallback || (screenshotMethod.value === 'nemu' && actualMethod !== 'nemu')) {
        statusType.value = 'warning'
        statusMessage.value = `已连接，但 NEMU 不可用，实际回退到 ${String(actualMethod || 'adb').toUpperCase()}`
        message.warning(statusMessage.value)
      } else {
        statusType.value = 'success'
        statusMessage.value = `连接成功，实际使用 ${String(actualMethod || '未知方式').toUpperCase()}`
        message.success(statusMessage.value)
      }
    } else {
      statusType.value = 'error'
      statusMessage.value = '连接失败'
      message.error('连接失败')
    }
  } catch (e) {
    statusType.value = 'error'
    statusMessage.value = getErrorMessage(e, '连接失败，请检查端口是否正确')
    message.error('连接失败')
  } finally {
    connecting.value = false
    refreshDeviceStatus()
  }
}

async function autoSelectScreenshot() {
  benchmarking.value = true
  benchmarkResult.value = null
  await saveSettings()
  try {
    const res = await api.device.benchmarkScreenshot(port.value, 5, 1, true)
    benchmarkResult.value = res.data
    if (res.data.fastest) {
      screenshotMethod.value = res.data.fastest
      await loadSettings()
      message.success(`已自动选择最快截图方式: ${res.data.fastest}`)
    } else {
      message.error('没有可用的截图方式')
    }
  } catch (e) {
    message.error(getErrorMessage(e, '截图测速失败'))
  } finally {
    benchmarking.value = false
  }
}

async function disconnect() {
  statusMessage.value = ''
  try {
    await api.device.connect(0)
    message.success('已断开')
  } catch {}
  actualMethod.value = ''
}

async function startGame() {
  gameLoading.value = true
  try {
    const res = await api.device.startGame()
    if (res.data.success !== false) {
      message.success('游戏启动成功')
    } else {
      message.error(res.data.error || '启动失败')
    }
  } catch (e) {
    message.error(getErrorMessage(e, '启动游戏失败'))
  } finally {
    gameLoading.value = false
  }
}

async function stopGame() {
  gameLoading.value = true
  try {
    const res = await api.device.stopGame()
    if (res.data.success !== false) {
      message.success('游戏已关闭')
    } else {
      message.error(res.data.error || '关闭失败')
    }
  } catch (e) {
    message.error(getErrorMessage(e, '关闭游戏失败'))
  } finally {
    gameLoading.value = false
  }
}

async function restartGame() {
  gameLoading.value = true
  try {
    const res = await api.device.restartGame()
    if (res.data.success !== false) {
      message.success('游戏重启成功')
    } else {
      message.error(res.data.error || '重启失败')
    }
  } catch (e) {
    message.error(getErrorMessage(e, '重启游戏失败'))
  } finally {
    gameLoading.value = false
  }
}

async function scan() {
  scanning.value = true
  devices.value = []
  try {
    const res = await api.device.scan()
    devices.value = Array.isArray(res.data) ? res.data : (res.data.devices || [])
  } catch (e) {
    message.error(getErrorMessage(e, '扫描失败'))
  } finally {
    scanning.value = false
  }
}

function applyDevice(dev: any) {
  port.value = dev.port
  devicePath.value = dev.path || ''
  deviceType.value = dev.type || ''
  api.config.save({
    port: dev.port,
    device_path: dev.path || '',
    device_type: dev.type || '',
    device_index: dev.index ?? 0,
  })
  saveSettings()
  message.success(`已应用设备: ${dev.name} (${dev.port})`)
}

onMounted(loadSettings)
</script>
