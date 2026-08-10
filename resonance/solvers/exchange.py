"""交易所进出与买卖工作流：进出交易所、切换买卖标签页、查找门店、交易流程。

  包括：
    - 进入/退出交易所 (enter_exchange / leave_exchange)
    - 在城市门店页定位并点击门店图标 (find_outlet)
    - 完整卖货流程 (sell_goods：全选→抬价→确认)
    - 完整买货流程 (buy_goods：委托 buy.buy_business)
  不包含：体力检测（由调用方在进入交易所前后自行调用 strength.check_shop_strength）
"""
import time
from typing import List, Literal, Optional, Tuple

from loguru import logger

from resonance.device.adb import ADB
from resonance.device.device import get_device, input_swipe, input_tap, screenshot, screenshot_image
from resonance.model import app
from resonance.solvers.buy import buy_business
from resonance.solvers.sell import click_bargain_button as _sell_bargain
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
EXCHANGE_OCR_KEYWORD = "交易所"
_EXCHANGE_TAB_POS = {"buy": (120, 670), "sell": (335, 670)}
_EXCHANGE_ENTRY_POS = {"buy": (960, 321), "sell": (960, 405)}


def _current_exchange_texts() -> List[str]:
    results = predict(screenshot_image(), no_crop=True)
    return [item["text"] for item in results]


def _is_exchange_opened(texts: List[str]) -> bool:
    if _is_exchange_entry(texts):
        return True
    return _is_exchange_tab("buy", texts) or _is_exchange_tab("sell", texts)


def _is_exchange_entry(texts: List[str]) -> bool:
    """Return whether the exchange landing page, not a trade tab, is open."""
    has_exchange_title = any("交易所" in text for text in texts)
    has_entry_action = any("我要买" in text or "我要卖" in text for text in texts)
    # The bottom buy/sell tabs are also visible on real trade pages.  Their
    # tab-specific OCR markers must therefore take precedence over entry text.
    has_trade_tab = _is_exchange_tab("buy", texts) or _is_exchange_tab("sell", texts)
    return has_exchange_title and has_entry_action and not has_trade_tab


def _is_exchange_tab(tab: Literal["buy", "sell"], texts: List[str]) -> bool:
    """Return whether OCR contains a tab-specific exchange marker.

    This check guards fixed-coordinate input.  Keep its markers deliberately
    narrow: generic labels such as "货舱" and "利润" also occur on the
    main screen and must never authorize a trade action.
    """
    markers = (
        ("全部买入", "预计买入", "买入总价", "DISPLAY")
        if tab == "buy"
        else ("全部卖出", "预计卖出", "卖出总价", "抬价幅度")
    )
    return any(marker in text for text in texts for marker in markers)


def _is_sell_page_ready(attempts: int = 2, interval: float = 0.35) -> bool:
    """Verify the sell tab before any fixed-coordinate sell input.

    OCR may transiently miss one label while the tab is opening, so this allows
    one short recheck.  A missing marker is treated as unsafe rather than
    guessing from UI colours or generic text.
    """
    for attempt in range(attempts):
        if _is_exchange_tab("sell", _current_exchange_texts()):
            return True
        if attempt + 1 < attempts:
            time.sleep(interval)
    return False


def _wait_exchange_open(timeout: float = 2.0, interval: float = 0.25) -> bool:
    """Wait only until an exchange marker appears after a known outlet tap."""
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if _is_exchange_opened(_current_exchange_texts()):
            return True
        if _current_scene() in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
            return True
        time.sleep(interval)
    return False


def _try_cached_outlet(city: Optional[str], name: str) -> bool:
    """Use a previously OCR-confirmed point only after verifying this city/name pair.

    The cache is strictly an in-process fast path. A failed verification
    removes it and falls through to dynamic OCR and scrolling.
    """
    if not city:
        return False
    pos = OUTLET_TAP_CACHE.get((city, name))
    if pos is None:
        return False
    logger.info(f"交易所缓存尝试: city={city}, pos={pos}")
    input_tap(pos)
    if _wait_exchange_open(timeout=1.5):
        logger.info(f"交易所缓存验证成功: city={city}")
        return True
    OUTLET_TAP_CACHE.pop((city, name), None)
    logger.info(f"交易所缓存失效，回退动态OCR: city={city}")
    return False


def _switch_exchange_tab(tab: Literal["buy", "sell"]) -> bool:
    texts = _current_exchange_texts()
    if _is_exchange_tab(tab, texts):
        return True

    other_tab: Literal["buy", "sell"] = "sell" if tab == "buy" else "buy"
    if _is_exchange_tab(other_tab, texts):
        logger.info(f"交易所{other_tab}页：点击底部{tab}页签")
        input_tap(_EXCHANGE_TAB_POS[tab])
        time.sleep(1.0)
        # A verified trade page must never fall back to a landing-page click.
        return _is_exchange_tab(tab, _current_exchange_texts())

    if not _is_exchange_entry(texts):
        return False

    # The exchange landing page has large "我要买 / 我要卖" buttons.  It is
    # not the trade-tab page, so the bottom buy/sell tab coordinates must not
    # be used here.  A following tab-specific OCR check is still required.
    entry_pos = _EXCHANGE_ENTRY_POS[tab]
    logger.info(f"交易所入口页：点击我要{'买' if tab == 'buy' else '卖'}")
    input_tap(entry_pos)
    time.sleep(1.0)
    return _is_exchange_tab(tab, _current_exchange_texts())


def _wait_exchange_ocr_click(
    timeout: float = 15.0,
    initial_results: Optional[List[dict]] = None,
    cache_key: Optional[Tuple[str, str]] = None,
) -> bool:
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
            if EXCHANGE_OCR_KEYWORD not in text:
                continue
            position = item["position"]
            x1 = position[0][0]
            x2 = position[2][0]
            # The outlet icon is below the whole OCR label.  Match by the
            # common keyword, but tap below the complete label's centre so a
            # long real name such as "交易所-武林市集" remains correctly aligned.
            center_x = int((x1 + x2) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            pos = (center_x, center_y + 35)
            logger.info(f"交易所OCR稳定命中: 交易所 (原始识别={text})")
            get_device().input_tap(pos[0], pos[1])
            if _wait_exchange_open():
                if cache_key is not None:
                    OUTLET_TAP_CACHE[cache_key] = pos
                    logger.info(f"交易所缓存已记录: city={cache_key[0]}, pos={pos}")
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
        cache_key = (city, name) if city else None
        if _try_cached_outlet(city, name):
            return True
        if _wait_exchange_ocr_click(timeout=3.0, initial_results=ocr_results, cache_key=cache_key):
            return True
        input_swipe((900, 260), (420, 560), swipe_time=700)
        time.sleep(0.5)
        if _wait_exchange_ocr_click(cache_key=cache_key):
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
        logger.info(f"交易所: 标题颜色未命中，根据页面标记继续")

    if _switch_exchange_tab(tab):
        return True

    texts = _current_exchange_texts()
    if _is_exchange_opened(texts):
        if _switch_exchange_tab(tab):
            return True
        logger.error(f"交易所已打开，但未能确认{tab}页签")
        return False

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


_SELL_CARGO_LOAD_REGION = ((1120, 370), (1255, 425))
_SELL_SETTLEMENT_REGION = ((100, 480), (1180, 610))
_SELL_RESULT_NOTICE_REGION = ((450, 320), (800, 395))
_SELL_PAGE_MARKER_REGION = ((850, 80), (1250, 130))


def _read_sell_cargo_load() -> Optional[int]:
    """Read the current value from the sell-page 载货量 current/capacity label."""
    results = predict(
        screenshot_image(),
        cropped_pos1=_SELL_CARGO_LOAD_REGION[0],
        cropped_pos2=_SELL_CARGO_LOAD_REGION[1],
    )
    text = "".join(str(item.get("text", "")).replace(" ", "") for item in results)
    for index, char in enumerate(text):
        if char != "/":
            continue
        left = text[:index]
        digits = "".join(char for char in reversed(left) if char.isdigit())
        if digits:
            value = int(digits[::-1])
            logger.debug(f"[卖货] 载货量识别: {value} ({text})")
            return value
    logger.error(f"[卖货] 载货量OCR失败: {text or 'empty'}")
    return None


def _select_all() -> None:
    """Click the sell-all control exactly once after cargo OCR confirms goods."""
    logger.debug("出售全部货物")
    input_tap((1187, 103))
    time.sleep(0.3)


def _bargain_sell(num: int = 0) -> bool:
    return _sell_bargain(num)


def _ocr_texts_in_region(region: Tuple[Tuple[int, int], Tuple[int, int]]) -> List[str]:
    results = predict(
        screenshot_image(),
        cropped_pos1=region[0],
        cropped_pos2=region[1],
    )
    return [str(item.get("text", "")) for item in results]


def _is_sell_settlement_visible() -> bool:
    """Recognize the post-sale settlement panel using only its body region.

    The full title is the primary proof.  The paired labels allow for a title
    OCR miss without treating generic exchange-page text as a settlement.
    """
    texts = _ocr_texts_in_region(_SELL_SETTLEMENT_REGION)
    if any("卖出结算报告" in text for text in texts):
        return True
    has_profit = any("总利润" in text for text in texts)
    has_tax = any("纳税" in text or "税额" in text for text in texts)
    return has_profit and has_tax


def _is_sell_page_still_visible() -> bool:
    """Check the sell-tab header locally after settlement detection misses."""
    texts = _ocr_texts_in_region(_SELL_PAGE_MARKER_REGION)
    return _is_exchange_tab("sell", texts)


def _has_no_sellable_goods_notice() -> bool:
    texts = _ocr_texts_in_region(_SELL_RESULT_NOTICE_REGION)
    return any("请选择要出售的交易品" in text for text in texts)


def _close_sell_settlement() -> None:
    """Dismiss a confirmed settlement panel without leaving the exchange.

    The second blank-area tap is reserved for a panel still visible after the
    first dismiss action, avoiding an unnecessary fixed-coordinate input.
    """
    input_tap((896, 676))
    time.sleep(0.5)
    if _is_sell_settlement_visible():
        input_tap((896, 676))


def _confirm_sell(before_load: int) -> bool:
    input_tap((1056, 647))

    # A successful sale transitions to a separate settlement panel, where the
    # sell-page cargo label no longer exists.  Verify that panel first, using
    # only two bounded OCR reads of its body region.
    for wait_seconds in (1.1, 0.9):
        time.sleep(wait_seconds)
        if _is_sell_settlement_visible():
            logger.info("[卖货] 检测到卖出结算报告，出售成功")
            _close_sell_settlement()
            return True

    if not _is_sell_page_still_visible():
        logger.error("[卖货] 未检测到结算页，且当前不在卖货页，无法确认出售成功")
        return False

    if _has_no_sellable_goods_notice():
        logger.info("[卖货] 出售全部未选中可卖交易品，本城市无可出售交易品")
        return True

    after_load = _read_sell_cargo_load()
    if after_load is None:
        logger.error("[卖货] 仍在卖货页但载货量OCR失败，无法确认出售成功")
        return False
    if after_load >= before_load:
        logger.error("[卖货] 出售后载货量未变化，无法确认出售成功")
        return False

    logger.info(f"[卖货] 载货量变化：{before_load} -> {after_load}，等待结算报告")
    time.sleep(0.6)
    if _is_sell_settlement_visible():
        _close_sell_settlement()
        return True
    logger.error("[卖货] 载货量已变化但未检测到结算页，安全停止")
    return False


def sell_goods(haggle: int = 0) -> bool:
    if not _is_sell_page_ready():
        logger.error("卖货前页面验证失败，拒绝点击固定坐标以避免误触")
        return False

    before_load = _read_sell_cargo_load()
    if before_load is None:
        logger.error("[卖货] 卖货前载货量OCR失败，拒绝执行卖货控件")
        return False
    if before_load == 0:
        logger.info("[卖货] 车厢为空，无需清货")
        return True
    _select_all()
    if not _bargain_sell(haggle):
        logger.error("出售货物失败：议价流程未完成")
        return False
    if not _confirm_sell(before_load):
        logger.error("出售货物失败：已选中货物，但出售确认未完成")
        return False
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
