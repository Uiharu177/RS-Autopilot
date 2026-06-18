export type SceneInfo = {
  label: string
  description: string
  type: 'default' | 'success' | 'info' | 'warning' | 'error'
}

const SCENE_MAP: Record<string, SceneInfo> = {
  MAIN_MAP: {
    label: '主页面/到站页面',
    description: '第一章入口页面；如果 OCR 出现右下“访问城市”，可进入城市门店页。',
    type: 'success',
  },
  CITY_VIEW: {
    label: '城市门店页',
    description: '包含商会、市政厅、铁安局、交易所、市场等门店名称。',
    type: 'info',
  },
  EXCHANGE: {
    label: '交易所入口页',
    description: '出现“交易所 + 我要买/我要卖”，可进入买入或卖出页。',
    type: 'info',
  },
  EXCHANGE_BUY: {
    label: '交易所买入页',
    description: '包含全部买入、预计买入、买入总价、DISPLAY 等标记。',
    type: 'success',
  },
  EXCHANGE_SELL: {
    label: '交易所卖出页',
    description: '包含全部卖出、预计卖出、卖出总价、货舱、WAREHOUSE 等标记。',
    type: 'success',
  },
  STATION_LIST: {
    label: '地图/站点列表',
    description: '第二章地图导航页面，通常出现“图示”。',
    type: 'info',
  },
  STATION_DETAIL: {
    label: '站点详情页',
    description: '包含“前往目的地”，正式跑商会从这里发车。',
    type: 'info',
  },
  TASK_DETAIL: {
    label: '任务详情页',
    description: '纠错流程会尝试返回关闭后继续恢复。',
    type: 'warning',
  },
  TRAVEL_CRUISE: {
    label: '行车中',
    description: '列车正在巡航，后端会监听到站、战斗和异常。',
    type: 'warning',
  },
  TRAVEL_MAP: {
    label: '行车地图',
    description: '行车相关页面。',
    type: 'warning',
  },
  BATTLE_CARD: {
    label: '战斗中',
    description: '行车中触发战斗，后端会等待战斗结束。',
    type: 'warning',
  },
  CRASH: {
    label: '游戏崩溃页',
    description: '识别到 Err0r/Error 或 EXIT GAME，后端会保存快照并重启恢复。',
    type: 'error',
  },
  LOADING: {
    label: '加载中',
    description: '过渡或加载页面。',
    type: 'warning',
  },
  LOGIN: {
    label: '登录/公告页',
    description: '后端接管会处理登录弹窗、公告和资源更新确认。',
    type: 'warning',
  },
  UNKNOWN: {
    label: '未知页面',
    description: '当前截图未能稳定匹配到已知场景。',
    type: 'warning',
  },
}

export function getSceneInfo(scene?: string | null): SceneInfo {
  if (!scene) {
    return { label: '未知', description: '暂无场景数据。', type: 'default' }
  }
  return SCENE_MAP[scene] || { label: scene, description: '暂未配置该场景的前端说明。', type: 'default' }
}
