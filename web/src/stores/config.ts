import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useConfigStore = defineStore('config', () => {
  const globalConfig = ref<Record<string, boolean>>({})
  const cityConfig = ref<Record<string, unknown>>({})
  const deviceSettings = ref({ port: 16384, touch_method: 'adb', screenshot_method: 'adb' })
  const loaded = ref(false)

  async function loadConfig() {
    try {
      const res = await api.config.get()
      const data = res.data
      const gc = data.config?.global_config || {}
      globalConfig.value = {
        is_exit_on_failure: gc.is_exit_on_failure ?? false,
        is_exit_on_fatigue: gc.is_exit_on_fatigue ?? false,
        use_stamina_item: gc.use_stamina_item ?? false,
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
