"""体力模块：检测体力是否充足、使用体力道具补充。

  核心函数：
    check_shop_strength() — OCR 读取体力数值，返回是否充足
    use_strength() — 进入体力页 → 尝试使用道具 → 关闭页面
    use_candy() — 按优先级遍历三种体力道具，OCR 点击使用
  备注：powered by 提神棒棒糖/口香糖/跳糖，不支持便当（use_food 保留）
"""

import time
from loguru import logger
from resonance.device.device import input_back, screenshot
from resonance.vision.color import BGR
from resonance.preset.control import click, find_text, ocr_click, wait_gbr


def check_shop_strength():
    image = screenshot()
    image.crop_image((959, 13), (1036, 38))
    text = image.ocr()
    if len(text) == 0:
        return True
    strength = text[0]["text"].split("/")
    cur_strength = int(strength[0])
    total_strength = int(strength[1])
    return total_strength - cur_strength > 60


def use_food():
    click((1107, 606))
    if not wait_gbr(
        (61, 130),
        BGR(26, 38, 91),
        BGR(26, 38, 91)
    ):
        logger.error("未找到便当页面")
        return False
    click((1077, 430))
    status = ocr_click("确认", cropped_pos1=(952, 485), cropped_pos2=(1022, 522))
    click((1077, 430))
    return status


USE_ITEMS = ["提神棒棒糖", "提神口香糖", "仙人掌提神跳糖"]


def use_candy():
    for item_text in USE_ITEMS:
        coord, _ = find_text(item_text, log=False)
        if coord:
            click(coord)
            time.sleep(1)
            if ocr_click("补充", log=False) or ocr_click("使用", log=False):
                time.sleep(1)
                input_back()
                return True
    logger.error("未找到可用的体力道具")
    return False


def use_strength():
    coord, _ = find_text("FATIGUE", log=False)
    if not coord:
        logger.error("未找到体力页面")
        return False
    return use_candy()
