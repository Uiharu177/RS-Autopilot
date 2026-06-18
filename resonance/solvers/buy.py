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

from resonance.device.device import input_back, input_swipe, input_tap, screenshot, screenshot_image
from resonance.utils.exception_handling import get_excption
from resonance.vision.color import BGR, HSV
from resonance.vision.ocr import predict
from resonance.preset import click, find_text, go_home
from resonance.preset.control import wait_gbr


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
                    logger.info("资金不足，跳过买货")
                    return True
                logger.info("资金充足")
                break

    if max_book > 0:
        for _ in range(max_book):
            _consume_one_book()

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


def buy_good(good: str, book: int, max_book: int, again: bool = False):
    logger.info(f"正在购买: {good}")
    pos, image = find_text(
        good,
        cropped_pos1=(622, 136),
        cropped_pos2=(854, 685),
        log=False,
    )
    if not pos:
        pos, image = find_good(good)
    if pos and image is not None:
        if _is_locked_good(pos[1]):
            logger.info(f"商品{good}未解锁，跳过")
            return False, book
        logger.info(f"点击商品: {good}")
        click(pos)
        time.sleep(0.3)
        return True, book
    else:
        return False, book


def _is_locked_good(pos_y: int) -> bool:
    y1 = max(136, pos_y + 12)
    y2 = min(685, pos_y + 60)
    image = screenshot()
    image.crop_image((622, y1), (854, y2))
    results = image.ocr()
    texts = [item["text"] for item in results]
    logger.debug(f"商品锁定检测OCR: {texts}")
    return any("解锁" in text or "声望" in text or "投资" in text or "声望达到" in text for text in texts)


def find_good(good, timeout=10):
    start = time.time()
    while (spend_time := time.time() - start) < timeout:
        if spend_time < timeout / 2:
            input_swipe((678, 558), (693, 314), swipe_time=500)
        else:
            input_swipe((693, 314), (678, 558), swipe_time=500)
        time.sleep(1)
        result, image = find_text(
            good,
            cropped_pos1=(622, 136),
            cropped_pos2=(854, 685),
            log=False,
        )
        if result:
            return result, image
    return None, None


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


def click_bargain_button(num=0):
    logger.info(f"议价次数: {num}")
    start = time.perf_counter()
    while time.perf_counter() - start < 15:
        if num <= 0:
            return True
        bgr = screenshot().get_bgr((1176, 461))
        logger.debug(f"降价界面颜色检查: {bgr}")
        if BGR(0, 123, 240) <= bgr <= BGR(2, 133, 255):
            input_tap((1177, 461))
            time.sleep(1.0)
        elif bgr == [251, 253, 253]:
            logger.info("降价次数不足")
            return True
        elif bgr == [62, 63, 63]:
            logger.info("疲劳不足")
            input_tap((83, 36))
            return True
        hsv = screenshot().crop_image((516, 224), (787, 439)).get_hsv((629, 271))
        logger.debug(f"降价是否成功颜色检查(HSV): {hsv}")
        if 95 <= hsv.h <= 105:
            logger.info("降价成功")
            num -= 1
        else:
            logger.info("降价失败")
        wait_gbr((628, 102), BGR(60, 55, 30), BGR(70, 65, 40))
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
