"""交易所进出与买卖工作流：进出交易所、切换买卖标签页、查找门店、交易流程。

  包括：
    - 进入/退出交易所 (enter_exchange / leave_exchange)
    - 在城市门店页定位并点击门店图标 (find_outlet)
    - 完整卖货流程 (sell_goods：全选→抬价→确认)
    - 完整买货流程 (buy_goods：委托 buy.buy_business)
  不包含：体力检测（由调用方在进入交易所前后自行调用 strength.check_shop_strength）
"""
import re
import time
from typing import List, Literal, Optional, Tuple

from loguru import logger

from resonance.device.adb import ADB
from resonance.device.device import get_device, input_swipe, input_tap, screenshot, screenshot_image
from resonance.model import app
from resonance.solvers.buy import buy_business
from resonance.solvers.sell import (
    is_empty_goods as _sell_goods_empty,
    click_bargain_button as _sell_bargain,
)
from resonance.vision.color import BGR
from resonance.vision.ocr import predict
from resonance.preset.control import blurry_ocr_click, ocr_click, wait_gbr
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.solvers.city import (
    CITY_NAMES,
    _current_scene,
    _get_recognizer,
    _guard_entry,
    _pick_city_name,
    enter_city_view,
)
from resonance.vision.image import Image
from resonance.utils.utils import RESOURCES_PATH


OUTLET_TAP_CACHE: dict[Tuple[str, str], Tuple[int, int]] = {}


def _current_exchange_texts() -> List[str]:
    results = predict(screenshot_image(), no_crop=True)
    return [item["text"] for item in results]


def _is_exchange_opened(texts: List[str]) -> bool:
    has_exchange_title = any("交易所" in text for text in texts)
    has_entry_action = any("我要买" in text or "我要卖" in text for text in texts)
    if has_exchange_title and has_entry_action:
        return True
    return _is_exchange_tab("buy", texts) or _is_exchange_tab("sell", texts)


def _is_exchange_tab(tab: Literal["buy", "sell"], texts: List[str]) -> bool:
    markers = (
        ("全部买入", "预计买入", "买入总价", "DISPLAY")
        if tab == "buy"
        else ("全部卖出", "预计卖出", "卖出总价", "货舱", "WAREHOUSE", "利润", "抬价幅度")
    )
    return any(marker in text for text in texts for marker in markers)


def _switch_exchange_tab(tab: Literal["buy", "sell"]) -> bool:
    texts = _current_exchange_texts()
    if not _is_exchange_opened(texts):
        return False
    if _is_exchange_tab(tab, texts):
        return True
    input_tap((120, 670) if tab == "buy" else (335, 670))
    time.sleep(1.0)
    return _is_exchange_tab(tab, _current_exchange_texts())


def _wait_exchange_ocr_click(timeout: float = 15.0, initial_results: Optional[List[dict]] = None) -> bool:
    aliases = ("交易所", "平交易所", "巫交易所", "亚交易所", "交易所-武林市集")
    start = time.perf_counter()
    pending_results = initial_results
    while time.perf_counter() - start < timeout:
        if _is_exchange_opened(_current_exchange_texts()):
            return True
        if _current_scene() in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
            return True
        results = pending_results if pending_results is not None else predict(screenshot_image())
        pending_results = None
        for item in results:
            text = item["text"]
            alias = next((alias for alias in aliases if alias in text), None)
            if not alias:
                continue
            position = item["position"]
            x1 = position[0][0]
            x2 = position[2][0]
            if len(text) > len(alias) and alias in text:
                alias_start = text.index(alias)
                alias_center = alias_start + len(alias) / 2
                center_x = int(x1 + (x2 - x1) * alias_center / max(len(text), 1))
            else:
                center_x = int((x1 + x2) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            pos = (center_x, center_y + 35)
            logger.info(f"交易所OCR稳定命中: {text} / {alias} => {pos}")
            get_device().input_tap(pos[0], pos[1])
            time.sleep(1.0)
            if _is_exchange_opened(_current_exchange_texts()):
                return True
            if Recognizer().scene in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
                return True
        time.sleep(0.25)
    return False


def _tap_shoggolith_exchange_fixed(city: Optional[str]) -> bool:
    if city != "修格里城":
        return False
    pos = (1030, 342)
    logger.info(f"交易所固定点: {pos}")
    get_device().input_tap(pos[0], pos[1])
    time.sleep(1.0)
    return _is_exchange_opened(_current_exchange_texts())


def _enter_shoggolith_exchange_fixed() -> bool:
    logger.info("交易所固定点")
    adb = ADB()
    try:
        if not adb.connect(app.Global.device.port):
            logger.error("修格里城交易所固定流程: ADB连接失败")
            return False
        logger.info("修格里城交易所固定流程: tap 1030 342")
        adb.device.shell("input tap 1030 342")
        time.sleep(1.0)
        if Recognizer().scene in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
            return True
        return _is_exchange_opened(_current_exchange_texts())
    finally:
        try:
            adb.kill()
        except Exception:
            pass


def find_outlet(name: str) -> bool:
    recog = Recognizer()
    scene = recog.scene
    ocr_results = recog.ocr()
    if name == "交易所" and _is_exchange_opened(_current_exchange_texts()):
        return True
    if name == "交易所":
        if recog.scene not in (Scene.CITY_VIEW, Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL) and not enter_city_view():
            return False
        if scene not in (Scene.CITY_VIEW, Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
            recog = Recognizer()
            scene = recog.scene
            ocr_results = recog.ocr()
        city = _pick_city_name(ocr_results)
        logger.info(f"前往 => {name}")
        if _wait_exchange_ocr_click(timeout=3.0, initial_results=ocr_results):
            return True
        input_swipe((900, 260), (420, 560), swipe_time=700)
        time.sleep(0.5)
        if _wait_exchange_ocr_click():
            return True
        if city == "修格里城":
            return _enter_shoggolith_exchange_fixed()
        logger.error(f"未找到门店: {name}")
        return False

    def _ocr_click_outlet(text: str, log: bool = False):
        score = 0.30 if name == "交易所" else 0.45
        offset = 35 if name == "交易所" else 80
        return (
            blurry_ocr_click(text, excursion_pos=(0, offset), log=log, score=score)
            or ocr_click(text, excursion_pos=(0, offset), log=log)
        )

    outlet_names = [name]
    if name == "交易所":
        outlet_names.extend(["平交易所", "亚交易所", "交易所-武林市集"])

    def _try_ocr_click(log: bool = False):
        for outlet_name in outlet_names:
            if result := _ocr_click_outlet(
                outlet_name, log=(log and outlet_name == outlet_names[-1])
            ):
                return result
        return False

    if not enter_city_view():
        return False
    logger.info(f"前往 => {name}")

    if result := _try_ocr_click():
        return result

    swipe_paths = [
        ((900, 260), (420, 560)),
        ((640, 260), (640, 610)),
        ((640, 610), (640, 260)),
        ((900, 360), (260, 360)),
        ((380, 360), (1020, 360)),
        ((910, 260), (360, 570)),
        ((370, 260), (920, 570)),
        ((920, 570), (360, 260)),
        ((360, 570), (920, 260)),
    ]
    for idx, (start_pos, end_pos) in enumerate(swipe_paths):
        input_swipe(start_pos, end_pos, swipe_time=700)
        time.sleep(0.5)
        if result := _try_ocr_click(log=(idx == len(swipe_paths) - 1)):
            return result

    logger.error(f"未找到门店: {name}")
    return False


def enter_exchange(tab: Literal["buy", "sell"] = "buy") -> bool:
    if _switch_exchange_tab(tab):
        return True

    scene = _current_scene()
    if scene not in (Scene.MAIN_MAP, Scene.CITY_VIEW, Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
        if not _guard_entry(
            {Scene.MAIN_MAP, Scene.CITY_VIEW, Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL}
        ):
            return False
        scene = _current_scene()

    if scene in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
        if _switch_exchange_tab(tab):
            return True
    elif scene == Scene.CITY_VIEW:
        if find_outlet("交易所") and _switch_exchange_tab(tab):
            return True
    else:
        if enter_city_view() and find_outlet("交易所") and _switch_exchange_tab(tab):
            return True

    is_join = wait_gbr(
        pos=(286, 35),
        min_gbr=BGR(250, 250, 250),
        max_gbr=BGR(255, 255, 255),
        cropped_pos1=(242, 11),
        cropped_pos2=(414, 66),
        trynum=5,
    )
    if not is_join:
        texts = _current_exchange_texts()
        if not _is_exchange_opened(texts):
            logger.error("进入交易所失败")
            return False
        logger.info(f"交易所标题颜色未命中，但检测到页面标记，继续选择页签: {texts[:8]}")

    if tab == "buy":
        input_tap((927, 321))
    elif tab == "sell":
        input_tap((932, 404))
    time.sleep(1.0)

    if _is_exchange_tab(tab, _current_exchange_texts()):
        return True

    bgr = screenshot().get_bgr((1175, 460))
    logger.debug(f"进入交易所颜色检查: {bgr}")
    if (
        BGR(0, 123, 240) <= bgr <= BGR(2, 133, 255)
        or BGR(220, 220, 220) <= bgr <= BGR(235, 235, 235)
        or BGR(0, 170, 240) <= bgr <= BGR(5, 185, 255)
        or BGR(80, 80, 80) <= bgr <= BGR(115, 115, 115)
        or BGR(120, 120, 120) <= bgr <= BGR(155, 155, 155)
    ):
        return True

    texts = _current_exchange_texts()
    if _is_exchange_opened(texts):
        logger.info(f"检测到交易所页面标记，放行进入交易所: {texts[:8]}")
        return True

    logger.error("进入交易所失败")
    return False


def leave_exchange():
    for _ in range(5):
        if screenshot().match_template(RESOURCES_PATH / "scene/main_map.png", 0.96):
            return True
        input_tap((83, 36))
        time.sleep(0.5)
    return screenshot().match_template(RESOURCES_PATH / "scene/main_map.png", 0.96)


# ========================================================================
# Sell workflow
# ========================================================================


def _select_all() -> bool:
    start = time.perf_counter()
    while time.perf_counter() - start < 15:
        image = screenshot()
        bgr = image.get_bgr((1156, 100))
        logger.debug(f"是否出售货物颜色检查 {bgr}")
        if not (bgr.b == 0 and bgr.g == 0 and 90 <= bgr.r <= 100):
            logger.debug("出售全部货物")
            input_tap((1187, 103))
            time.sleep(0.5)
            break
    if _sell_goods_empty():
        logger.error("检测到未成功出售物品")
        return False
    return True


def _bargain_sell(num: int = 0) -> bool:
    return _sell_bargain(num)


def _confirm_sell() -> bool:
    for _ in range(3):
        input_tap((1056, 647))
        time.sleep(0.8)
        bgr = screenshot().get_bgr((1175, 470), offset=5)
        logger.debug(f"卖出按钮点击后颜色检查: {bgr}")
        if bgr == [227, 131, 82]:
            logger.info("检测到包含本地商品提示，确认继续")
            input_tap((975, 498))
            time.sleep(0.5)
            continue
        if not (
            BGR(0, 170, 240) <= bgr <= BGR(5, 185, 255)
            or bgr == [227, 131, 82]
            or bgr == [251, 253, 253]
        ):
            return True
    return False


def sell_goods(haggle: int = 0) -> bool:
    if not _select_all():
        logger.info("无货物可卖，跳过卖货")
        return True
    if not _bargain_sell(haggle):
        return False
    if not _confirm_sell():
        return False
    time.sleep(0.5)
    input_tap((896, 676))
    time.sleep(0.5)
    input_tap((896, 676))
    return True


# ========================================================================
# Buy workflow
# ========================================================================


def buy_goods(
    primary_goods: List[str],
    secondary_goods: List[str],
    haggle: int = 0,
    book: int = 0,
):
    return buy_business(primary_goods, secondary_goods, haggle, max_book=book)
