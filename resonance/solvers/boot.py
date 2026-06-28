"""游戏启动模块 — 万能启动入口。

   boot_game() 检测当前状态并自动处理：
   - 模拟器未运行 → 启动模拟器
   - 游戏未运行 → 启动游戏
   - 登录页 → 点击进入
   - 加载中 → 等待
   - 弹窗/公告 → 关闭
   - 行车中 → 等到站
   - 业务页 → 回首页
   - 已在主页 → 识别城市

   返回值：城市名（str）或 None
"""

import time
from typing import Optional

from loguru import logger

from resonance.device.device import (
    connect,
    is_game_foreground,
    launch_emulator,
    start_game,
)
from resonance.model import app
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.solvers.navigation import travel_monitor
from resonance.solvers.recovery import (
    RecoveryContext,
    handle_startup_interruption,
    identify_city,
    recover_to_expected,
    safe_go_home,
)


def _detect_travel(scene: Scene) -> bool:
    return scene in (Scene.TRAVEL_CRUISE, Scene.TRAVEL_MAP, Scene.BATTLE_CARD)


_BUSINESS_SCENES = {
    Scene.EXCHANGE,
    Scene.EXCHANGE_BUY,
    Scene.EXCHANGE_SELL,
    Scene.SHOP,
    Scene.STATION_DETAIL,
    Scene.STATION_LIST,
    Scene.TASK_DETAIL,
    Scene.UNKNOWN_WITH_NAVBAR,
}


def boot_game(port: Optional[int] = None) -> Optional[str]:
    """万能启动入口：不管当前什么状态，返回当前城市名或 None。"""
    launch_emulator(port or 0)

    for attempt in range(1, 4):
        if connect(port):
            break
        logger.warning(f"连接设备失败 ({attempt}/3)，重试...")
        time.sleep(3)
    else:
        logger.error("设备连接失败，放弃启动")
        return None

    for outer in range(3):
        if not is_game_foreground():
            logger.info("游戏不在前台，启动游戏")
            if not start_game():
                logger.error("启动游戏失败")
                time.sleep(3)
                continue
            result = recover_to_expected(
                RecoveryContext(
                    step="BOOT_AFTER_START",
                    expected_scenes={Scene.MAIN_MAP, Scene.CITY_VIEW},
                    allow_travel=True,
                    max_attempts=20,
                )
            )
            if result.ok and result.state:
                city = result.state.city or identify_city() or _resolve_fallback()
                if city:
                    return city
            continue

        recog = Recognizer()
        if handle_startup_interruption(recog):
            time.sleep(2)
            continue

        scene = recog.scene
        logger.info(f"启动循环 #{outer} 场景={scene.name}")

        if _detect_travel(scene):
            logger.info("检测到行车中，等待到站")
            try:
                if travel_monitor():
                    continue
            except Exception:
                logger.warning("行车监控异常，走恢复流程")

        if scene in _BUSINESS_SCENES:
            logger.info(f"在业务页面 {scene.name}，返回首页")
            safe_go_home()
            city = identify_city()
            if city:
                logger.info(f"返回首页成功，当前城市: {city}")
                return city
            continue

        if scene in (Scene.MAIN_MAP, Scene.CITY_VIEW):
            city = identify_city()
            if city:
                logger.info(f"游戏已在可读状态，当前城市: {city}")
                return city

        result = recover_to_expected(
            RecoveryContext(
                step="BOOT_TAKEOVER",
                expected_scenes={Scene.MAIN_MAP, Scene.CITY_VIEW},
                allow_travel=True,
                max_attempts=16,
            )
        )
        if result.ok and result.state:
            city = result.state.city or identify_city() or _resolve_fallback()
            if city:
                logger.info(f"启动恢复完成，当前城市: {city}")
                return city

        time.sleep(3)

    logger.error("启动失败：所有重试耗尽")
    return None


def _resolve_fallback() -> Optional[str]:
    fallback = app.RunBuy.BuyCity or app.RunBuy.SellCity
    if fallback:
        logger.warning(f"城市识别失败，使用配置城市: {fallback}")
        return fallback
    return None
