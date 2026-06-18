from typing import Optional, Set

import cv2 as cv

from resonance.scene.scene import Scene
from resonance.vision.color import BGR


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    texts = [item["text"] for item in ocr_results]
    has_buy_page = any(
        marker in text
        for text in texts
        for marker in ("全部买入", "预计买入", "买入总价", "DISPLAY")
    )
    has_sell_page = any(
        marker in text
        for text in texts
        for marker in ("全部卖出", "预计卖出", "卖出总价", "货舱", "WAREHOUSE", "利润", "抬价幅度")
    )
    if has_buy_page:
        return Scene.EXCHANGE_BUY
    if has_sell_page:
        return Scene.EXCHANGE_SELL

    has_entry = any("我要买" in text or "我要卖" in text for text in texts)
    has_exchange = any("交易所" in text for text in texts)
    if has_entry and has_exchange:
        return Scene.EXCHANGE

    try:
        bgr = img[35, 286]  # (y, x) in OpenCV
        b = int(bgr[0]); g = int(bgr[1]); r = int(bgr[2])
        color = BGR(b, g, r)
        if not (BGR(248, 248, 248) <= color <= BGR(255, 255, 255)):
            return None
    except Exception:
        return None

    if "买入" in text_set or "出售" in text_set or "全部出售" in text_set:
        if "买入" in text_set:
            return Scene.EXCHANGE_BUY
        return Scene.EXCHANGE_SELL
    return Scene.EXCHANGE
