import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

type StopAction = 'stay_there' | 'goto_main' | 'close_game'
type FatigueAction = 'none' | StopAction

interface GlobalConfig {
  use_stamina_item: boolean
  on_stop_action: StopAction
  fatigue_action: FatigueAction
}

export const useConfigStore = defineStore('config', () => {
  const globalConfig = ref<GlobalConfig>({
    use_stamina_item: false,
    on_stop_action: 'stay_there',
    fatigue_action: 'none',
  })
  const cityConfig = ref<Record<string, unknown>>({})
  const deviceSettings = ref({ port: 16384, touch_method: 'adb', screenshot_method: 'adb' })
  const loaded = ref(false)

  async function loadConfig() {
    try {
      const res = await api.config.get()
      const data = res.data
      const gc = data.config?.global_config || {}
      globalConfig.value = {
        use_stamina_item: gc.use_stamina_item ?? false,
        on_stop_action: gc.on_stop_action ?? 'stay_there',
        fatigue_action: gc.fatigue_action ?? 'none',
      }
      const app = data.app?.Global || {}
      deviceSettings.value.port = app.device?.port ?? 16384
      deviceSettings.value.touch_method = app.touch_method || 'adb'
      deviceSettings.value.screenshot_method = app.screenshot_method || 'adb'
      loaded.value = true
    } catch {
      loaded.value = true
    }
  }

  async function loadCityConfig() {
    try {
      const res = await api.config.getCityConfig()
      cityConfig.value = res.data
    } catch {}
  }

  async function saveGlobalConfig() {
    try {
      await api.config.save({ global_config: { ...globalConfig.value } })
    } catch {}
  }

  async function saveDeviceSettings() {
    try {
      await api.config.save({ ...deviceSettings.value })
    } catch {}
  }

  async function saveCityConfig() {
    try {
      await api.config.saveCityConfig(cityConfig.value)
    } catch {}
  }

  watch(globalConfig, saveGlobalConfig, { deep: true })
  watch(deviceSettings, saveDeviceSettings, { deep: true })

  return {
    globalConfig,
    cityConfig,
    deviceSettings,
    loaded,
    loadConfig,
    loadCityConfig,
    saveGlobalConfig,
    saveDeviceSettings,
    saveCityConfig,
  }
})
