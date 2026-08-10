"""卖货业务：出售准备、议价、卖出确认与卖出结算报告关闭。

调用方必须先确认已处于交易所卖出页。本模块不负责进入、切换或离开交易所。
"""

import time
from typing import List, Optional, Tuple

from loguru import logger

from resonance.device.device import input_tap, screenshot_image
from resonance.solvers.exchange import _current_exchange_texts, _is_exchange_tab
from resonance.solvers.purchase import _read_bargain_percent, _wait_bargain_stable
from resonance.vision.ocr import predict


_SALE_LOAD_REGION = ((1120, 370), (1255, 425))
_SALE_SETTLEMENT_REGION = ((100, 480), (1180, 610))
_SALE_PAGE_MARKER_REGION = ((850, 80), (1250, 130))


def _read_sale_load() -> Optional[int]:
    """Read the current sell-page cargo value from its current/capacity label."""
    results = predict(
        screenshot_image(),
        cropped_pos1=_SALE_LOAD_REGION[0],
        cropped_pos2=_SALE_LOAD_REGION[1],
    )
    text = "".join(str(item.get("text", "")).replace(" ", "") for item in results)
    for index, char in enumerate(text):
        if char != "/":
            continue
        left = text[:index]
        digits = "".join(char for char in reversed(left) if char.isdigit())
        if digits:
            value = int(digits[::-1])
            logger.debug(f"[卖货] 载货量识别：value={value}, ocr={text}")
            return value
    logger.error(f"[卖货] 载货量 OCR 失败：ocr={text or 'empty'}")
    return None


def _select_all_for_sale() -> None:
    logger.debug("[卖货] 执行出售全部货物")
    input_tap((1187, 103))
    time.sleep(0.3)


def negotiate_sale_price(num=0, max_attempts=6) -> bool:
    """Run the verified sale-side price negotiation sequence."""
    logger.info(f"[卖货] 议价设置：count={num}")
    attempts = 0
    while True:
        if num <= 0:
            return True
        if attempts >= max_attempts:
            logger.warning(f"[卖货] 议价已达到尝试上限，继续出售确认：max_attempts={max_attempts}")
            return True

        before = _read_bargain_percent()
        input_tap((1177, 461))
        time.sleep(0.3)
        after = _wait_bargain_stable()
        attempts += 1

        if after is not None and before is not None and after != before:
            logger.info(f"[卖货] 议价成功：before={before}%, after={after}%")
            num -= 1
            if after >= 20:
                logger.info(f"[卖货] 议价幅度达到阈值，结束议价：percent={after}%")
                return True
        else:
            logger.debug("[卖货] 单次议价未生效")


def _sale_ocr_texts(region: Tuple[Tuple[int, int], Tuple[int, int]]) -> List[str]:
    results = predict(
        screenshot_image(),
        cropped_pos1=region[0],
        cropped_pos2=region[1],
    )
    return [str(item.get("text", "")) for item in results]


def _is_sell_settlement_visible() -> bool:
    texts = _sale_ocr_texts(_SALE_SETTLEMENT_REGION)
    if any("卖出结算报告" in text for text in texts):
        return True
    has_profit = any("总利润" in text for text in texts)
    has_tax = any("纳税" in text or "税额" in text for text in texts)
    return has_profit and has_tax


def _is_sale_page_visible() -> bool:
    return _is_exchange_tab("sell", _sale_ocr_texts(_SALE_PAGE_MARKER_REGION))


def _close_sell_settlement() -> None:
    input_tap((896, 676))
    time.sleep(0.5)
    if _is_sell_settlement_visible():
        input_tap((896, 676))


def _is_sale_page_ready(attempts: int = 2, interval: float = 0.35) -> bool:
    for attempt in range(attempts):
        if _is_exchange_tab("sell", _current_exchange_texts()):
            return True
        if attempt + 1 < attempts:
            time.sleep(interval)
    return False


def _confirm_sale(before_load: int) -> bool:
    input_tap((1056, 647))

    for wait_seconds in (1.1, 0.9):
        time.sleep(wait_seconds)
        if _is_sell_settlement_visible():
            logger.info("[卖货] 卖出结算报告已确认，出售成功")
            _close_sell_settlement()
            return True

    if not _is_sale_page_visible():
        logger.error("[卖货] 出售确认失败，未检测到结算页且当前不在卖货页")
        return False

    after_load = _read_sale_load()
    if after_load is None:
        logger.error("[卖货] 出售确认失败，仍在卖货页但载货量 OCR 失败")
        return False
    if after_load == before_load:
        logger.info("[卖货] 出售后载货量未变化，本城市无可出售交易品，清仓步骤完成")
        return True
    if after_load > before_load:
        logger.error(
            f"[卖货] 出售确认失败，载货量异常增加：before={before_load}, after={after_load}"
        )
        return False

    logger.info(f"[卖货] 载货量已变化，等待结算报告：before={before_load}, after={after_load}")
    time.sleep(0.6)
    if _is_sell_settlement_visible():
        _close_sell_settlement()
        return True
    logger.error("[卖货] 出售确认失败，载货量已变化但未检测到结算报告")
    return False


def execute_sale_flow(haggle: int = 0) -> bool:
    """Complete one sale flow on a confirmed sell page."""
    if not _is_sale_page_ready():
        logger.error("[卖货] 页面验证失败，拒绝执行固定坐标出售操作")
        return False

    before_load = _read_sale_load()
    if before_load is None:
        logger.error("[卖货] 卖出前载货量 OCR 失败，拒绝执行出售操作")
        return False
    if before_load == 0:
        logger.info("[卖货] 车厢为空，无需出售")
        return True

    _select_all_for_sale()
    if not negotiate_sale_price(haggle):
        logger.error("[卖货] 出售准备失败，议价流程未完成")
        return False
    if not _confirm_sale(before_load):
        logger.error("[卖货] 出售确认失败，已执行卖出操作但未完成状态验证")
        return False
    return True
