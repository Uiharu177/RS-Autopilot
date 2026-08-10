"""买货模块：商品列表扫描、购买、议价、进货书使用、满载检测。

  核心函数：buy_business(primary_goods, secondary_goods, num, max_book)
    - 按优先级扫描商品列表
    - 使用进货书、议价、确认购买
    - 检测载货量，满载自动停止
  不包含：进入交易所、体力检测、退出交易所（由 exchange.py 或调用方负责）
"""

import time
from typing import List, Literal, Optional, Tuple

import cv2 as cv
import numpy as np
from loguru import logger

from resonance.device import device as device_state
from resonance.device.device import input_back, input_swipe_hold, input_tap, screenshot, screenshot_image
from resonance.vision.ocr import predict
from resonance.preset import click


def buy_business(
    primary_goods: List[str],
    secondary_goods: List[str],
    num: int = 0,
    max_book: int = 0,
):
    book_used = 0

    def _consume_one_book():
        nonlocal book_used
        if book_used >= max_book:
            return
        book_used += 1
        logger.info(f"使用进货书: {book_used}/{max_book}")
        input_tap((1081, 100))
        # The item panel may still be handling quantity/selection state after
        # it first appears.  Do not turn this flow into an eager poll: an early
        # confirmation can make the no-quantity-change path exit the purchase.
        time.sleep(2.0)
        results = predict(screenshot_image())
        found = False
        for item in results:
            if "进货" not in item["text"]:
                continue
            pos = item["position"]
            cy = int((pos[0][1] + pos[2][1]) / 2)
            logger.info(f"找到进货书行: y={cy}")
            input_tap((920, cy))
            time.sleep(2.0)
            found = True
            break
        if found:
            for _ in range(3):
                popup = predict(screenshot_image(), cropped_pos1=(300, 420), cropped_pos2=(1050, 560))
                for pop_item in popup:
                    pop_text = pop_item["text"]
                    if "确定" in pop_text or "确认" in pop_text:
                        pcx = int((pop_item["position"][0][0] + pop_item["position"][2][0]) / 2)
                        pcy = int((pop_item["position"][0][1] + pop_item["position"][2][1]) / 2)
                        logger.info(f"进货书确认弹窗: ({pcx},{pcy})")
                        input_tap((pcx, pcy))
                        time.sleep(2.0)
                        return
                time.sleep(0.5)
        input_back()
        time.sleep(1.5)

    full_boatload = False
    invalid_page = False

    boatload = get_boatload()
    if boatload < 0:
        if _dismiss_popup():
            boatload = get_boatload()
    if boatload < 0:
        logger.error("当前页面无法检测载货量，停止买货")
        return False
    if boatload == 0:
        logger.info("已满载，进入下一步")
        return True

    # 资金检查：先试买第一个商品，如果载货量没变 → 没钱
    if primary_goods:
        for probe_good in primary_goods:
            prev_load = get_boatload()
            ok, _ = buy_good(probe_good, 0, max_book)
            if ok:
                time.sleep(0.5)
                if get_boatload() == prev_load:
                    logger.warning("资金不足，终止跑商")
                    device_state.STOP = True
                    return False
                logger.info("资金充足")
                if max_book > 0:
                    for _ in range(max_book):
                        _consume_one_book()
                break

    def process_goods(good):
        nonlocal full_boatload, invalid_page
        boatload = get_boatload()
        if boatload < 0:
            if _dismiss_popup():
                boatload = get_boatload()
        if boatload < 0:
            logger.error("当前页面无法检测载货量，停止买货")
            invalid_page = True
            return False
        if boatload == 0:
            logger.info("已满载")
            full_boatload = True
            return True
        prev = boatload
        result, _ = buy_good(good, 0, max_book)
        if not result:
            logger.info(f"商品{good}购买失败")
            return False
        time.sleep(0.5)
        new_boatload = get_boatload()
        if new_boatload == 0:
            logger.info("已满载，停止遍历剩余商品")
            full_boatload = True
            return True
        if new_boatload == prev:
            logger.info(f"载货量暂未变化 ({prev}% -> {new_boatload}%)，仅复查，不重复点击同一商品")
            time.sleep(0.5)
            new_boatload = get_boatload()
        if new_boatload == prev:
            logger.info(f"载货量仍未变化 ({prev}% -> {new_boatload}%)，不重复点击，跳过")
        else:
            logger.info(f"剩余载货量: {new_boatload}%")
        return True

    for good in primary_goods:
        process_goods(good)
        if full_boatload or invalid_page:
            break
    if not full_boatload and not invalid_page:
        for good in secondary_goods:
            process_goods(good)
            if full_boatload or invalid_page:
                break
    if invalid_page:
        return False
    if not is_purchase_selection_empty():
        if not click_bargain_button(num):
            logger.error("购买物品失败：议价流程未完成")
            return False
        return click_buy_button()
    if full_boatload:
        logger.info("已满载但购物车为空，进入下一步")
        return True
    else:
        logger.info("商品列表已扫描完，未购买物品，进入下一步")
        return True


def is_purchase_selection_empty():
    """Return whether the buy-page selection list is empty.

    This is not a cargo-hold check: it verifies that this purchase has at
    least one selected item before bargaining and pressing the buy button.
    """
    image = screenshot()
    image.crop_image((870, 132), (994, 205))
    bgr = image.get_bgr((898, 169))
    logger.debug(f"购买清单是否为空检查 {bgr}")
    return bgr.r < 40 and bgr.g < 40 and bgr.b < 40


def _chars_diff(a: str, b: str) -> int:
    """计算两个等长字符串的字符差异数"""
    return sum(1 for ca, cb in zip(a, b) if ca != cb)


def _ocr_goods_list():
    """OCR 商品列表区域，返回完整 data"""
    image = screenshot()
    image.crop_image((580, 130), (854, 685))
    return image.ocr()


_GoodState = Literal["absent", "locked", "buyable", "uncertain"]
_LOCK_MARKERS = ("投资", "声望", "解锁", "锁定", "未开放")


def _ocr_center(item: dict) -> Tuple[float, float]:
    position = item["position"]
    return (
        (position[0][0] + position[2][0]) / 2,
        (position[0][1] + position[2][1]) / 2,
    )


def _is_good_name(text: str, good: str) -> bool:
    return text == good or (
        len(text) == len(good)
        and _chars_diff(text, good) == 1
        and (text[0] == good[0] or text[-1] == good[-1])
    )


def _classify_good_candidate(data: list[dict], item: dict) -> _GoodState:
    """Classify one matched product row without ever treating missing data as buyable.

    Product names, price percentages and lock hints move slightly with OCR and
    UI scale, but they remain inside the same ~one-card-height band.  A lock
    hint always wins.  Missing evidence is deliberately "uncertain" so a
    covered lock label can never turn into a blind click.
    """
    cx, cy = _ocr_center(item)
    card_items = []
    for other in data:
        ox, oy = _ocr_center(other)
        # A product card is about 110 px high.  Percentages and lock labels
        # belong under the product name, with a small tolerance above it for
        # OCR bounding-box jitter.
        if cy - 12 <= oy <= cy + 72 and abs(ox - cx) <= 170:
            card_items.append((other["text"], ox, oy))

    lock_text = next((text for text, _, _ in card_items if any(marker in text for marker in _LOCK_MARKERS)), None)
    if lock_text:
        logger.info(f"商品卡锁定检测命中: y={cy:.0f}, text={lock_text}")
        return "locked"

    if any(text.rstrip().endswith("%") for text, _, _ in card_items):
        return "buyable"

    return "uncertain"


def _find_good_state(data: list[dict], good: str) -> Tuple[_GoodState, Optional[Tuple[int, int]]]:
    """Return the target item's conservative state and click point, if safe."""
    for item in data:
        text = item["text"]
        if not _is_good_name(text, good):
            continue
        cx, cy = _ocr_center(item)
        state = _classify_good_candidate(data, item)
        pos = (int(cx), int(cy))
        if state == "buyable":
            logger.info(f"商品卡可购买: 目标={good}, OCR={text}, pos={pos}")
        elif state == "uncertain":
            logger.info(f"商品卡状态不确定，暂不点击: 目标={good}, OCR={text}, y={cy:.0f}")
        return state, pos
    return "absent", None


def _match_good_name(data, good):
    """Compatibility helper: only expose a click point for a confirmed card."""
    state, pos = _find_good_state(data, good)
    return pos if state == "buyable" else None


def _is_locked(data, pos_y):
    """Compatibility helper for callers that only have a product row Y value."""
    y1 = pos_y - 12
    y2 = pos_y + 72
    for item in data:
        text = item["text"]
        oy = (item["position"][0][1] + item["position"][2][1]) / 2
        if y1 <= oy <= y2:
            if any(marker in text for marker in _LOCK_MARKERS):
                logger.info(f"锁定检测命中: y={oy:.0f}, text={text}")
                return True
    return False


def _goods_signature(data):
    """商品签名：商品名+y坐标集合，用于滑到顶/底检测。
    过滤百分比和纯数字，只保留长度≥2的文本。
    y坐标四舍五入到10px粒度，避免OCR抖动导致签名不同。"""
    sig = []
    for item in data:
        text = item["text"]
        if len(text) < 2 or text.endswith("%") or text.replace(".", "").replace(",", "").isdigit():
            continue
        y = int((item["position"][0][1] + item["position"][2][1]) / 2 / 10) * 10
        sig.append((text, y))
    return tuple(sorted(sig))


def buy_good(good: str, book: int, max_book: int, again: bool = False):
    logger.info(f"正在购买: {good}")
    # 商品列表是类似短视频的分页流：手指上 -> 下回到前面的商品，
    # 手指下 -> 上查看后面的商品。先用前者归顶，再用后者单向搜索到底。
    swipe_to_top = ((693, 314), (678, 558))
    swipe_toward_bottom = ((678, 558), (693, 314))

    def try_current_page(data: list[dict]) -> Tuple[_GoodState, Optional[Tuple[int, int]]]:
        state, pos = _find_good_state(data, good)
        if state != "uncertain":
            return state, pos

        # A dialogue or a transient render can hide a card label for one OCR
        # frame. Retry briefly, but never transform uncertainty into a click.
        for retry in range(1, 3):
            time.sleep(0.4)
            state, pos = _find_good_state(_ocr_goods_list(), good)
            if state in ("buyable", "locked"):
                logger.info(f"商品卡短重试 {retry}/2: {state}")
                return state, pos
            # A one-frame OCR miss cannot prove that the earlier incomplete
            # card disappeared.  Keep the conservative uncertain state.
        logger.warning(f"商品{good}卡片信息持续不完整，保守跳过，不执行整页往返搜索")
        return "uncertain", pos

    def click_if_buyable(data: list[dict]) -> Optional[bool]:
        state, pos = try_current_page(data)
        if state == "locked":
            logger.info(f"商品{good}未解锁，跳过")
            return False
        if state == "uncertain":
            return False
        if state != "buyable" or pos is None:
            return None
        logger.info(f"点击商品: {good}, pos={pos}")
        click(pos)
        time.sleep(0.3)
        return True

    # 先在当前页面找
    data = _ocr_goods_list()
    result = click_if_buyable(data)
    if result is not None:
        return result, book

    # 阶段1：先归位到列表顶部。手指上 -> 下会回到前面的卡片，
    # 直到画面不再变化即表示已经到达顶部。归位阶段只移动，不点击，避免漏掉
    # 顶部卡片或在中途改变购买顺序。
    last_sig = _goods_signature(data)
    for _ in range(10):
        input_swipe_hold(*swipe_to_top, swipe_time=500, hold_ms=400)
        time.sleep(0.8)
        data = _ocr_goods_list()
        sig = _goods_signature(data)
        if sig == last_sig:
            logger.info("已归位列表顶部，开始手指下 -> 上逐屏搜索")
            break
        last_sig = sig
    else:
        logger.info(f"未能归位到商品列表顶部: {good}")
        return False, book

    # 阶段2：从顶部单向向下搜索。手指下 -> 上会查看后面的卡片，
    # 移动，逐屏检查并在命中后立即点击，不再做第二次完整往返。
    last_sig = None
    same_count = 0
    for _ in range(20):
        result = click_if_buyable(data)
        if result is not None:
            return result, book

        sig = _goods_signature(data)
        if sig == last_sig:
            same_count += 1
            if same_count >= 2:
                logger.info("已滑到底，停止搜索")
                break
        else:
            same_count = 0
        last_sig = sig

        input_swipe_hold(*swipe_toward_bottom, swipe_time=500, hold_ms=400)
        time.sleep(0.8)
        data = _ocr_goods_list()

    logger.info(f"未找到商品: {good}")
    return False, book


def _dismiss_popup() -> bool:
    """关闭弹窗（进货书确认等），返回是否关闭了弹窗"""
    results = predict(screenshot_image(), cropped_pos1=(250, 420), cropped_pos2=(1050, 580))
    for item in results:
        text = item["text"]
        if "确认" in text or "确定" in text:
            cx = int((item["position"][0][0] + item["position"][2][0]) / 2)
            cy = int((item["position"][0][1] + item["position"][2][1]) / 2)
            logger.info(f"关闭弹窗: 点击 {text} => ({cx},{cy})")
            input_tap((cx, cy))
            time.sleep(1.5)
            return True
    return False


def get_boatload():
    image = screenshot_image()
    results = predict(image, cropped_pos1=(500, 70), cropped_pos2=(1260, 130))
    texts = [item["text"] for item in results]
    markers = ("交易品", "货舱", "全部买入", "全部卖出", "预计买入", "预计卖出")
    if not any(marker in text for text in texts for marker in markers):
        logger.warning(f"当前页面未检测到交易所买卖页标记: {texts}")
        return -1

    lower_color_bound = np.array([35, 35, 35])
    upper_color_bound = np.array([36, 36, 36])

    y = 418
    x_start = 872
    x_end = 1240

    row_segment = image[y : y + 1, x_start:x_end]
    mask = cv.inRange(row_segment, lower_color_bound, upper_color_bound)
    boatload = np.sum(mask == 255) / (x_end - x_start)
    return int(boatload * 100)


def _read_bargain_percent():
    """OCR读取议价幅度百分比，成功返回int，失败返回None"""
    import re
    results = predict(screenshot_image(), cropped_pos1=(900, 440), cropped_pos2=(1050, 480))
    for item in results:
        numbers = re.findall(r"-?\d+", item["text"])
        if numbers:
            return int(numbers[0])
    return None


def _wait_bargain_stable(timeout=3.0):
    """点击后反复读幅度数字，直到连续两次相同则认为动画结束"""
    start = time.perf_counter()
    last = None
    while time.perf_counter() - start < timeout:
        val = _read_bargain_percent()
        if val is not None and val == last:
            return val
        last = val
        time.sleep(0.3)
    return _read_bargain_percent()


def click_bargain_button(num=0, max_attempts=6):
    logger.info(f"议价次数: {num}")
    attempts = 0
    while True:
        if num <= 0:
            return True
        if attempts >= max_attempts:
            logger.warning(f"议价尝试次数已达上限({max_attempts})")
            return True

        before = _read_bargain_percent()
        input_tap((1177, 461))
        time.sleep(0.3)
        after = _wait_bargain_stable()
        attempts += 1

        if after is not None and before is not None and after != before:
            logger.info(f"降价成功 ({before}%→{after}%)")
            num -= 1
            if after >= 20:
                logger.info(f"砍价幅度已达{after}%，停止议价")
                return True
        else:
            logger.info("降价失败")
    return False


_BUY_SETTLEMENT_REGION = ((100, 480), (1180, 610))


def _buy_settlement_texts() -> List[str]:
    results = predict(
        screenshot_image(),
        cropped_pos1=_BUY_SETTLEMENT_REGION[0],
        cropped_pos2=_BUY_SETTLEMENT_REGION[1],
    )
    return [str(item.get("text", "")) for item in results]


def _is_buy_settlement_visible() -> bool:
    """Recognize the buy settlement panel from its body only.

    This avoids the old buy-button colour loop and does not OCR the full page.
    """
    texts = _buy_settlement_texts()
    if any("买入结算报告" in text for text in texts):
        return True
    has_tax = any("纳税" in text or "税额" in text for text in texts)
    has_total = any("买入总价" in text for text in texts)
    return has_tax and has_total


def _close_buy_settlement() -> None:
    """Dismiss a confirmed buy settlement before leaving the exchange."""
    input_tap((896, 676))
    time.sleep(0.5)
    if _is_buy_settlement_visible():
        input_tap((896, 676))


def click_buy_button() -> bool:
    """Click buy once and wait for the bounded buy-settlement transition."""
    input_tap((1056, 647))
    for wait_seconds in (1.1, 0.9):
        time.sleep(wait_seconds)
        if _is_buy_settlement_visible():
            logger.info("[买货] 检测到买入结算报告，购买成功")
            _close_buy_settlement()
            return True
    logger.error("[买货] 未检测到买入结算报告，无法确认购买成功")
    return False
