"""城市识别与进城：识别当前站点、判断是否在城市视图、进入城市。

  核心函数：
    identify_city() — OCR 识别当前所在城市
    enter_city_view() — 从主地图进入城市门店页
    is_city_view() — 判断当前是否在城市视图
  依赖：navigation.go_city（进城点击）、recovery.recover_to_expected（guard 失败时恢复）
"""
import time
from typing import List, Optional, Set, Tuple

from loguru import logger

from resonance.device.device import ensure_game_foreground, input_tap, screenshot, screenshot_image
from resonance.model import app
from resonance.solvers.navigation import go_city as _go_city
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.solvers.recovery import RecoveryContext, recover_to_expected
from resonance.vision.ocr import predict
from resonance.utils.utils import RESOURCES_PATH, read_json


CITY_OUTLET_MARKERS = (
    "交易所", "商会", "市集", "工会", "俱乐部",
    "铁安局", "市政厅", "奶茶店", "研究所", "休息区", "市场",
)

CITY_NAMES = tuple(read_json(RESOURCES_PATH / "goods/CityGoodsSellData.json", {}).keys())

_recognizer: Optional[Recognizer] = None
_recognizer_ts: float = 0.0
_RECOGNIZER_TTL: float = 2.0


def _get_recognizer() -> Recognizer:
    global _recognizer, _recognizer_ts
    now = time.perf_counter()
    if _recognizer is None or (now - _recognizer_ts) > _RECOGNIZER_TTL:
        _recognizer = Recognizer()
        _recognizer_ts = now
    return _recognizer


def _pick_city_name(results: List[dict]) -> Optional[str]:
    for item in results:
        text = item["text"]
        for city in CITY_NAMES:
            if city and city in text:
                return city
    return None


def identify_city_from_current_screen() -> Optional[str]:
    recog = _get_recognizer()
    invalid_scenes = (Scene.LOGIN, Scene.CRASH, Scene.LOADING, Scene.UNDEFINED)
    if recog.scene in invalid_scenes:
        logger.debug(f"跳过城市识别：当前场景 {recog.scene.name} 不包含城市信息")
        return None
    frame = recog.image
    for pos1, pos2 in (
        ((0, 430), (560, 710)),
        ((120, 120), (560, 710)),
    ):
        city = _pick_city_name(predict(frame, cropped_pos1=pos1, cropped_pos2=pos2))
        if city:
            logger.info(f"当前站点: {city}")
            return city
    city = _pick_city_name(recog.ocr())
    if city:
        logger.info(f"当前站点: {city}")
        return city
    return None


def recover_to_entry(expected_scenes: Optional[Set] = None, max_attempts: int = 12) -> bool:
    if not ensure_game_foreground():
        logger.error("接管失败：无法切回游戏前台")
        return False
    if expected_scenes is None:
        expected_scenes = {Scene.MAIN_MAP, Scene.CITY_VIEW}
    result = recover_to_expected(
        RecoveryContext(
            step="CITY_ENTRY",
            expected_scenes=expected_scenes,
            allow_travel=True,
            max_attempts=max_attempts,
        )
    )
    if not result.ok:
        logger.error(f"接管失败: {result.reason}")
    return result.ok


def _current_scene():
    return _get_recognizer().scene


def _guard_entry(expected_scenes: Set, max_attempts: int = 12) -> bool:
    scene = _current_scene()
    if scene in expected_scenes:
        logger.debug(f"入口轻量放行: {scene.name}")
        return True
    if scene in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL) and any(
        s in expected_scenes for s in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL)
    ):
        logger.debug(f"入口交易所轻量放行: {scene.name}")
        return True
    logger.info(f"入口需要恢复: current={scene.name}, expected={[s.name for s in expected_scenes]}")
    return recover_to_entry(expected_scenes=expected_scenes, max_attempts=max_attempts)


def is_city_view() -> bool:
    results = predict(screenshot_image())
    outlet_hits = sum(
        1
        for item in results
        if any(marker in item["text"] for marker in CITY_OUTLET_MARKERS)
    )
    if outlet_hits >= 2:
        return True
    return screenshot().crop_image(
        cropped_pos1=(25, 634), cropped_pos2=(99, 707)
    ).match_template(RESOURCES_PATH / "scene/fame.png", 0.95)


def identify_city() -> str:
    city = identify_city_from_current_screen()
    if city:
        return city
    input_tap((1170, 493))
    time.sleep(1.0)
    res = predict(screenshot_image(), cropped_pos1=(166, 520), cropped_pos2=(470, 600))
    city = _pick_city_name(res)
    if not city:
        raise ValueError("未识别到当前城市")
    logger.info(f"当前站点: {city}")
    return city


def enter_city_view(max_attempts: int = 10) -> bool:
    recog_scene = _current_scene()
    if recog_scene == Scene.CITY_VIEW:
        return True
    if recog_scene in (Scene.MAIN_MAP, Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
        return _go_city(max_attempts)
    if not _guard_entry({Scene.MAIN_MAP, Scene.CITY_VIEW}):
        return False
    return _go_city(max_attempts)
