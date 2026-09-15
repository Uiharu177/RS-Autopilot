"""卖货业务：出售准备、议价、卖出确认与卖出结算报告关闭。

调用方必须先确认已处于交易所卖出页。本模块不负责进入、切换或离开交易所。
"""

import time
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger

from resonance.device.device import input_tap, screenshot, screenshot_image
from resonance.solvers.exchange import _current_exchange_texts, _is_exchange_tab
from resonance.solvers.purchase import _read_bargain_percent, _wait_bargain_stable
from resonance.vision.ocr import number_predict, predict
from resonance.vision.image import Image


_SALE_LOAD_REGION = ((1120, 370), (1255, 425))
_SALE_SETTLEMENT_REGION = ((100, 480), (1180, 610))
_SALE_PAGE_MARKER_REGION = ((850, 80), (1250, 130))
_SALE_SLASH_TEMPLATE = Path(__file__).resolve().parents[2] / "resources" / "mask" / "slash.png"
_SALE_SLASH_THRESHOLD = 0.90
_SALE_DIGIT_WINDOW = 45


def _valid_load(current_text: str, capacity_text: str) -> Optional[int]:
    if not current_text.isdigit() or not capacity_text.isdigit():
        return None
    if len(current_text) > 1 and current_text.startswith("0"):
        return None
    if len(capacity_text) not in (3, 4) or capacity_text.startswith("0"):
        return None
    current, capacity = int(current_text), int(capacity_text)
    if not 100 <= capacity <= 9999 or current > capacity:
        return None
    return current


def _parse_sale_load_text(text: str) -> Optional[int]:
    text = "".join(text.split())
    if "/" in text:
        if text.count("/") != 1:
            return None
        left, right = text.split("/")
        return _valid_load(left, right)
    if not text.isdigit() or len(text) < 5:
        return None
    candidates = set()
    for capacity_length in (3, 4):
        if len(text) > capacity_length:
            value = _valid_load(text[:-capacity_length], text[-capacity_length:])
            if value is not None:
                candidates.add(value)
    for capacity_length in (3, 4):
        if len(text) > capacity_length + 1:
            value_text, capacity_text = text[:-capacity_length], text[-capacity_length:]
            if value_text[-1] == capacity_text[0]:
                value = _valid_load(value_text[:-1], capacity_text)
                if value is not None:
                    candidates.add(value)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _read_sale_load() -> Optional[int]:
    """Read the current sell-page cargo value from its current/capacity label."""
    has_template = _SALE_SLASH_TEMPLATE is not None and (
        not isinstance(_SALE_SLASH_TEMPLATE, Path) or _SALE_SLASH_TEMPLATE.is_file()
    )
    frame = screenshot_image()
    if has_template:
        match = Image(frame).crop_image(*_SALE_LOAD_REGION).match_template(_SALE_SLASH_TEMPLATE, _SALE_SLASH_THRESHOLD)
        x, y = match.loc
        if not match.status or match.score < _SALE_SLASH_THRESHOLD or not (
            _SALE_LOAD_REGION[0][0] < x < _SALE_LOAD_REGION[1][0]
            and _SALE_LOAD_REGION[0][1] < y < _SALE_LOAD_REGION[1][1]
        ):
            logger.error(f"[卖货] 斜杠模板匹配无效：score={match.score}, loc={match.loc}")
            return None
        left = Image(frame).crop_image(
            (max(_SALE_LOAD_REGION[0][0], x - _SALE_DIGIT_WINDOW), _SALE_LOAD_REGION[0][1]),
            (x - 2, _SALE_LOAD_REGION[1][1]),
        ).number_ocr()
        right = Image(frame).crop_image(
            (x + 2, _SALE_LOAD_REGION[0][1]),
            (min(_SALE_LOAD_REGION[1][0], x + _SALE_DIGIT_WINDOW), _SALE_LOAD_REGION[1][1]),
        ).number_ocr()
        if len(left) != 1 or len(right) != 1:
            logger.error(f"[卖货] 左右载货量 OCR 候选不唯一：left={left}, right={right}")
            return None
        left_text = "".join(str(left[0].get("text", "")).split())
        right_text = "".join(str(right[0].get("text", "")).split())
        value = _valid_load(left_text, right_text)
        if value is None:
            logger.error(f"[卖货] 左右载货量 OCR 校验失败：left={left_text!r}, right={right_text!r}")
        else:
            logger.info(f"[卖货] 模板分区识别载货量：current={value}, capacity={right_text}, slash={match.loc}, score={match.score:.3f}")
        return value
    results = number_predict(
        frame,
        cropped_pos1=_SALE_LOAD_REGION[0],
        cropped_pos2=_SALE_LOAD_REGION[1],
    )
    text = "".join(str(item.get("text", "")) for item in results)
    value = _parse_sale_load_text(text)
    if value is not None:
        return value

    # OCR may merge the current value and capacity into one numeric token when
    # the slash is faint or misread. Try a dynamic three/four-digit capacity
    # suffix, and only accept an unambiguous current value within that capacity.
    if text.isdigit():
        # A lost or digit-like slash must still occupy one character.  Shorter
        # text cannot safely distinguish current/capacity from a bare value.
        if len(text) < 5:
            logger.error(f"[卖货] 载货量 OCR 失败：ocr={text}")
            return None

        candidates: set[int] = set()
        for capacity_length in (4, 3):
            if len(text) <= capacity_length:
                continue
            value_text, capacity_text = text[:-capacity_length], text[-capacity_length:]
            if capacity_text.startswith("0"):
                continue
            value = int(value_text)
            capacity = int(capacity_text)
            if 100 <= capacity <= 9999 and 0 <= value <= capacity:
                candidates.add(value)

            # A slash can be misread as the first digit of the capacity, e.g.
            # ``627/1073`` -> ``62711073``. Strip that repeated boundary digit
            # only after the normal split is invalid.
            if (
                value > capacity
                and value_text[-1] == capacity_text[0]
                and len(value_text) > 1
            ):
                fixed_value = int(value_text[:-1])
                if 0 <= fixed_value <= capacity:
                    candidates.add(fixed_value)

        if len(candidates) == 1:
            value = next(iter(candidates))
            logger.debug(f"[卖货] 载货量动态容错解析：value={value}, ocr={text}")
            return value
        if len(candidates) > 1:
            logger.error(
                f"[卖货] 载货量 OCR 结果不唯一：candidates={sorted(candidates)}, ocr={text}"
            )
            return None

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
