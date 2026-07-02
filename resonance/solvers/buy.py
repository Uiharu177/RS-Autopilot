"""买货模块：商品列表扫描、购买、议价、进货书使用、满载检测。

  核心函数：buy_business(primary_goods, secondary_goods, num, max_book)
    - 按优先级扫描商品列表
    - 使用进货书、议价、确认购买
    - 检测载货量，满载自动停止
  不包含：进入交易所、体力检测、退出交易所（由 exchange.py 或调用方负责）
"""

import time
from typing import List

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
        time.sleep(2.0)
        results = predict(screenshot_image())
        found = False
        for item in results:
            text = item["text"]
            if "进货" in text:
                pos = item["position"]
                cx = int((pos[0][0] + pos[2][0]) / 2)
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
        if new_boatload == prev:
            logger.info(f"载货量未变化 ({prev}% -> {new_boatload}%)，重试一次")
            time.sleep(0.5)
            result, _ = buy_good(good, 0, max_book)
            if result:
                time.sleep(0.5)
                new_boatload = get_boatload()
        if new_boatload == prev:
            logger.info(f"载货量仍未变化 ({prev}% -> {new_boatload}%)，跳过")
        else:
            logger.info(f"剩余载货量: {new_boatload}%")
        return True

    for good in primary_goods:
        if process_goods(good):
            pass
    for good in secondary_goods:
        if process_goods(good):
            pass
    if invalid_page:
        return False
    if not is_empty_goods():
        click_bargain_button(num)
        click_buy_button()
        time.sleep(0.5)
        input_tap((896, 676))
        return True
    if full_boatload:
        logger.info("已满载但购物车为空，进入下一步")
        return True
    else:
        logger.info("商品列表已扫描完，未购买物品，进入下一步")
        return True


def is_empty_goods():
    image = screenshot()
    image.crop_image((870, 132), (994, 205))
    bgr = image.get_bgr((898, 169))
    logger.debug(f"货物是否为空检查 {bgr}")
    return bgr.r < 40 and bgr.g < 40 and bgr.b < 40


def _chars_diff(a: str, b: str) -> int:
    """计算两个等长字符串的字符差异数"""
    return sum(1 for ca, cb in zip(a, b) if ca != cb)


def _ocr_goods_list():
    """OCR 商品列表区域，返回完整 data"""
    image = screenshot()
    image.crop_image((580, 130), (854, 685))
    return image.ocr()


def _match_good_name(data, good):
    """在 OCR data 里找商品名，返回 (cx, cy) 或 None。
    匹配规则：完全相等，或等长且仅差1字且首/尾字相同。
    位置验证：下方 +10~35px 内必须有百分比文本（endswith %），否则视为价格行误识别。"""
    for item in data:
        text = item["text"]
        if not (text == good or (len(text) == len(good) and _chars_diff(text, good) == 1 and (text[0] == good[0] or text[-1] == good[-1]))):
            continue
        cy = (item["position"][0][1] + item["position"][2][1]) / 2
        cx = (item["position"][0][0] + item["position"][2][0]) / 2
        has_pct_below = False
        for other in data:
            oy = (other["position"][0][1] + other["position"][2][1]) / 2
            if cy + 10 <= oy <= cy + 35 and other["text"].endswith("%"):
                has_pct_below = True
                break
        if not has_pct_below:
            logger.info(f"匹配{good}(OCR={text})但下方无百分比，疑似误识别: y={cy:.0f}")
            continue
        pos = (int(cx), int(cy))
        logger.info(f"匹配商品: 目标={good}, OCR={text}, pos={pos}")
        return pos
    return None


def _is_locked(data, pos_y):
    """检查商品名下方 +10~55px 内是否有锁文本（投资/声望/解锁）"""
    y1 = pos_y + 10
    y2 = pos_y + 55
    for item in data:
        text = item["text"]
        oy = (item["position"][0][1] + item["position"][2][1]) / 2
        if y1 <= oy <= y2:
            if "投资" in text or "声望" in text or "解锁" in text:
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

    # 先在当前页面找
    data = _ocr_goods_list()
    pos = _match_good_name(data, good)
    if pos:
        if _is_locked(data, pos[1]):
            logger.info(f"商品{good}未解锁，跳过")
            return False, book
        logger.info(f"点击商品: {good}, pos={pos}")
        click(pos)
        time.sleep(0.3)
        return True, book

    # 阶段1：从当前位置下滑搜索
    last_sig = _goods_signature(data)
    same_count = 0
    for _ in range(20):
        input_swipe_hold((693, 314), (678, 558), swipe_time=500, hold_ms=400)
        time.sleep(0.8)
        data = _ocr_goods_list()
        pos = _match_good_name(data, good)
        if pos:
            if _is_locked(data, pos[1]):
                logger.info(f"商品{good}未解锁，跳过")
                return False, book
            logger.info(f"点击商品: {good}, pos={pos}")
            click(pos)
            time.sleep(0.3)
            return True, book

        sig = _goods_signature(data)
        if sig == last_sig:
            same_count += 1
            if same_count >= 2:
                logger.info("已滑到底，上滑到顶再搜")
                break
        else:
            same_count = 0
        last_sig = sig
    else:
        logger.info(f"未找到商品: {good}")
        return False, book

    # 阶段2：上滑到顶
    last_sig = _goods_signature(data)
    for _ in range(10):
        input_swipe_hold((678, 558), (693, 314), swipe_time=500, hold_ms=400)
        time.sleep(0.8)
        data = _ocr_goods_list()
        sig = _goods_signature(data)
        if sig == last_sig:
            logger.info("已滑到顶")
            break
        last_sig = sig

    # 阶段3：从顶下滑搜索
    last_sig = None
    same_count = 0
    for _ in range(20):
        data = _ocr_goods_list()
        pos = _match_good_name(data, good)
        if pos:
            if _is_locked(data, pos[1]):
                logger.info(f"商品{good}未解锁，跳过")
                return False, book
            logger.info(f"点击商品: {good}, pos={pos}")
            click(pos)
            time.sleep(0.3)
            return True, book

        sig = _goods_signature(data)
        if sig == last_sig:
            same_count += 1
            if same_count >= 2:
                logger.info("已滑到底，停止搜索")
                break
        else:
            same_count = 0
        last_sig = sig

        input_swipe_hold((693, 314), (678, 558), swipe_time=500, hold_ms=400)
        time.sleep(0.8)

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


def click_bargain_button(num=0, max_attempts=8):
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


def click_buy_button():
    start = time.time()
    while time.time() - start < 10:
        input_tap((1056, 647))
        time.sleep(1)
        image = screenshot()
        bgr = image.get_bgr((1177, 459), offset=5)
        logger.debug(f"购买物品界面颜色检查: {bgr}")
        if bgr != [2, 133, 253] and bgr != [251, 253, 253]:
            return True
    return False
