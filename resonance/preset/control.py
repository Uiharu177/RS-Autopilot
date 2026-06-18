from pathlib import Path
import time
from typing import Tuple, Union

import cv2 as cv
from loguru import logger

from resonance.vision.color import BGR
from resonance.device.device import input_tap, screenshot
from resonance.utils.exception_handling import get_excption
from resonance.utils.utils import RESOURCES_PATH


def wait_gbr(
    pos: Tuple[int, int],
    min_gbr: BGR,
    max_gbr: BGR,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    trynum=10,
):
    for _ in range(trynum):
        image = screenshot()
        image.crop_image(cropped_pos1, cropped_pos2)
        bgr = image.get_bgr(pos)
        logger.debug(f"等待指定坐标的颜色: {bgr}")
        if min_gbr <= bgr <= max_gbr:
            return True
        time.sleep(1)
    logger.info(get_excption())
    return False


def click_image(
    template: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    excursion_pos: Tuple[int, int] = (0, 0),
    trynum=10,
    check_err=True,
):
    time.sleep(0.5)
    for _ in range(trynum):
        image = screenshot()
        image.crop_image(cropped_pos1, cropped_pos2)
        result = image.match_template(template, 0.95)
        if result:
            pos = (
                result.loc[0] + excursion_pos[0],
                result.loc[1] + excursion_pos[1],
            )
            input_tap(pos)
            return True
    if check_err:
        logger.error(f"未找到指定图片 => {template}")
        logger.info(get_excption())
    return False


def click(pos):
    input_tap(pos)


def ocr_click(
    text: str,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    excursion_pos: Tuple[int, int] = (0, 0),
    trynum=3,
    log=True,
):
    for _ in range(trynum):
        image = screenshot()
        image.crop_image(cropped_pos1, cropped_pos2)
        data = image.ocr()
        coordinates = None
        for item in data:
            if item["text"] == text:
                position = item["position"]
                center_x = (position[0][0] + position[2][0]) / 2
                center_y = (position[0][1] + position[2][1]) / 2
                coordinates = (center_x + excursion_pos[0], center_y + excursion_pos[1])
                break
        if coordinates:
            input_tap(coordinates)
            return True
        time.sleep(1)
    if log:
        logger.error(f"未找到指定文本 => {text}")
    return False


def blurry_ocr_click(
    text: str,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    excursion_pos: Tuple[int, int] = (0, 0),
    trynum=3,
    log=True,
    score=0.7,
    click_first=False,
):
    for _ in range(trynum):
        image = screenshot()
        image.crop_image(cropped_pos1, cropped_pos2)
        data = image.ocr()
        coordinates = None
        for item in data:
            if text in item["text"] and len(text) / len(item["text"]) >= score:
                position = item["position"]
                if click_first:
                    center_x = position[0][0]
                    center_y = position[0][1]
                else:
                    center_x = (position[0][0] + position[2][0]) / 2
                    center_y = (position[0][1] + position[2][1]) / 2
                coordinates = (center_x + excursion_pos[0], center_y + excursion_pos[1])
                break
        if coordinates:
            input_tap(coordinates)
            return True
        time.sleep(1)
    if log:
        logger.error(f"未找到指定文本 => {text}")
    return False


def find_text(
    text: str,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    log=True,
):
    image = screenshot()
    image.crop_image(cropped_pos1, cropped_pos2)
    data = image.ocr()
    for item in data:
        if text in item["text"]:
            if log:
                logger.info(f"找到文本 => {text}")
            position = item["position"]
            center_x = int((position[0][0] + position[2][0]) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            return (center_x, center_y), image
    if log:
        logger.error(f"未找到指定文本 => {text}")
    return None, image


def go_home():
    logger.info("返回主界面")
    while screenshot().match_template(RESOURCES_PATH / "scene/main_map.png", 0.96) == False:
        time.sleep(1)
        logger.debug("尝试返回主界面")
        click_image(
            RESOURCES_PATH / "control/go_home.png",
            (154, 9),
            (243, 67),
            trynum=1,
            check_err=False,
        )
