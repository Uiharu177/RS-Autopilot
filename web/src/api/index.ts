import axios from 'axios'

export const API_ORIGIN = 'http://127.0.0.1:15177'
export const WS_ORIGIN = 'ws://127.0.0.1:15177'
export const API_BASE = `${API_ORIGIN}/api`

export function getErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as any
    return data?.error || data?.message || fallback
  }
  return fallback
}

export function debugFileUrl(filename?: string) {
  if (!filename) return ''
  const path = filename.replace(/^logs[\\/]debug[\\/]/, '').replace(/\\/g, '/')
  return `${API_BASE}/debug/files/${encodeURIComponent(path)}`
}

const api = {
  device: {
    scan: () => axios.get(`${API_BASE}/device/scan`),
    connect: (port: number) => axios.post(`${API_BASE}/device/connect`, { port }),
    status: () => axios.get(`${API_BASE}/device/status`),
    restartGame: () => axios.post(`${API_BASE}/device/restart-game`),
    startGame: () => axios.post(`${API_BASE}/device/start-game`),
    stopGame: () => axios.post(`${API_BASE}/device/stop-game`),
    benchmarkScreenshot: (port: number, samples = 5, warmup = 1, applyFastest = false) =>
      axios.post(`${API_BASE}/device/benchmark-screenshot`, { port, samples, warmup, apply_fastest: applyFastest }),
    debugOcr: () => axios.post(`${API_BASE}/device/debug-ocr`),
  },
  config: {
    get: () => axios.get(`${API_BASE}/config/get`),
    save: (data: Record<string, unknown>) => axios.post(`${API_BASE}/config/save`, data),
    getCityConfig: () => axios.get(`${API_BASE}/config/city-config`),
    saveCityConfig: (data: Record<string, unknown>) => axios.post(`${API_BASE}/config/city-config`, data),
  },
  scheduler: {
    start: () => axios.post(`${API_BASE}/scheduler/start`),
    stop: () => axios.post(`${API_BASE}/scheduler/stop`),
    status: () => axios.get(`${API_BASE}/scheduler/status`),
  },
  status: {
    scene: () => axios.get(`${API_BASE}/status/scene`),
  },
  business: {
    cities: () => axios.get(`${API_BASE}/business/cities`),
    start: (buyCity: string, sellCity: string) =>
      axios.post(`${API_BASE}/business/start`, { buy_city: buyCity, sell_city: sellCity }),
    startCities: (cities: string[]) =>
      axios.post(`${API_BASE}/business/start`, { cities }),
    stop: () => axios.post(`${API_BASE}/business/stop`),
  },
  debug: {
    snapshot: (templates: string[] = [], reason = 'frontend') =>
      axios.post(`${API_BASE}/debug/snapshot`, { templates, reason }),
    logs: () => axios.get(`${API_BASE}/debug/logs`),
    readLog: (filename: string, limit = 500) =>
      axios.get(`${API_BASE}/debug/logs/${filename}`, { params: { limit } }),
    timeline: (filename: string) =>
      axios.get(`${API_BASE}/debug/timeline/${filename}`),
    screenshots: () => axios.get(`${API_BASE}/debug/screenshots`),
    screenshotUrl: (filename: string) =>
      `${API_BASE}/debug/screenshot/${encodeURIComponent(filename)}`,
    getFile: (filename: string) => axios.get(`${API_BASE}/debug/files/${filename}`, { responseType: 'blob' }),
    tradePageFlow: (buyCity?: string, sellCity?: string, rounds = 1) =>
      axios.post(`${API_BASE}/debug/trade-page-flow`, { buy_city: buyCity, sell_city: sellCity, rounds }),
    tradePageFlowCities: (cities: string[], rounds = 1) =>
      axios.post(`${API_BASE}/debug/trade-page-flow`, { cities, rounds }),
  },
}

export default api
