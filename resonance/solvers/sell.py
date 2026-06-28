"""卖货模块：全选货物、抬价（议价）、确认卖出。

  核心函数：sell_business(num) — 全选→抬价→确认卖出。
  不包含：进入交易所、体力检测、退出交易所（由 exchange.py 或调用方负责）
"""

import time

from loguru import logger

from resonance.device.device import input_tap, screenshot
from resonance.solvers.buy import _read_bargain_percent, _wait_bargain_stable
from resonance.utils.exception_handling import get_excption
from resonance.vision.color import BGR
from resonance.preset.control import wait_gbr


def sell_business(num=0):
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 15:
        image = screenshot()
        bgr = image.get_bgr((1156, 100))
        logger.debug(f"是否出售货物颜色检查 {bgr}")
        if not (bgr.b == 0 and bgr.g == 0 and 90 <= bgr.r <= 100):
            logger.debug(f"出售全部货物颜色检查 {bgr}")
            input_tap((1187, 103))
            time.sleep(0.5)
            break
    if is_empty_goods():
        logger.error("检测到未成功出售物品")
        return False
    else:
        click_bargain_button(num)
        click_sell_button()
        time.sleep(0.5)
        input_tap((896, 676))
        time.sleep(0.5)
        input_tap((896, 676))
        return input_tap((896, 676))


def is_empty_goods():
    image = screenshot()
    image.crop_image((870, 132), (994, 205))
    bgr = image.get_bgr((898, 169))
    logger.debug(f"货物是否为空检查 {bgr}")
    return BGR(25, 33, 33) == bgr


def click_bargain_button(num=0, max_attempts=8):
    logger.info(f"议价次数: {num}")
    attempts = 0
    start = time.perf_counter()
    while time.perf_counter() - start < 15:
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
            logger.info(f"抬价成功 ({before}%→{after}%)")
            num -= 1
            if after >= 20:
                logger.info(f"抬价幅度已达{after}%，停止议价")
                return True
        else:
            logger.info("抬价失败")
        wait_gbr((629, 101), BGR(30, 50, 65), BGR(40, 60, 75))
    return False


def click_sell_button():
    start = time.time()
    while time.time() - start < 10:
        input_tap((1056, 647))
        time.sleep(1)
        image = screenshot()
        bgr = image.get_bgr((1175, 470), offset=5)
        logger.debug(f"出售物品界面颜色检查: {bgr}")
        if bgr == [227, 131, 82]:
            logger.info("检测到包含本地商品")
            input_tap((975, 498))
        if bgr != [0, 183, 253] and bgr != [227, 131, 82] and bgr != [251, 253, 253]:
            return True
    return False
