"""视觉工具底层：模板匹配、图像裁剪、颜色提取、图像保存/显示。

  这些函数被 Image 类（resonance/vision/image.py）封装为链式接口。
  不直接对外暴露，上层代码应使用 Image 类。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Tuple, Union

import cv2 as cv
import numpy as np
from loguru import logger

from resonance.vision.color import BGR, HSV


@dataclass
class MATCH_TEMPLATE_RESULT:
    score: float
    loc: Tuple[int, int]
    status: bool = True

    def __str__(self):
        return f"score: {self.score}, loc: {self.loc} status: {self.status}"

    def __bool__(self):
        return self.status

    def __eq__(self, value: object) -> bool:
        return self.status == bool(value)


def crop_image(
    image: cv.typing.MatLike,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
):
    if cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0):
        image = image[cropped_pos1[1] : cropped_pos2[1], cropped_pos1[0] : cropped_pos2[0]]
    return image


def _normalize_match_image(image: cv.typing.MatLike):
    if image is None:
        return None
    image = np.asarray(image)
    if image.size == 0:
        return None
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if image.ndim == 2:
        return cv.cvtColor(image, cv.COLOR_GRAY2BGR)
    if image.ndim != 3:
        return None
    if image.shape[2] == 1:
        return cv.cvtColor(image, cv.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv.cvtColor(image, cv.COLOR_BGRA2BGR)
    if image.shape[2] >= 3:
        return image[:, :, :3]
    return None


def match_template(
    image: cv.typing.MatLike,
    template: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    threshold: float = 0.8,
    no_crop: bool = False
) -> MATCH_TEMPLATE_RESULT:
    if isinstance(template, Path):
        template = str(template)
    if isinstance(template, str):
        template = cv.imread(template)
    if (cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0)) and not no_crop:
        image = crop_image(image, cropped_pos1, cropped_pos2)

    image = _normalize_match_image(image)
    template = _normalize_match_image(template)
    if image is None or template is None:
        logger.error("模板匹配失败: 截图或模板图片无效")
        return MATCH_TEMPLATE_RESULT(score=0.0, loc=(0, 0), status=False)

    if image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
        logger.debug(f"截图({image.shape})小于模板({template.shape})，跳过匹配")
        return MATCH_TEMPLATE_RESULT(score=0.0, loc=(0, 0), status=False)

    result = cv.matchTemplate(image, template, cv.TM_CCORR_NORMED)
    length, width, __ = template.shape
    _, score, _, max_loc = cv.minMaxLoc(result)
    max_loc = (max_loc[0] + cropped_pos1[0], max_loc[1] + cropped_pos1[1])
    return MATCH_TEMPLATE_RESULT(
        score=score,
        loc=(
            int(max_loc[0] + (width / 2)),
            int(max_loc[1] + (length / 2)),
        ),
        status=score >= threshold,
    )


def get_bgr(
    image: cv.typing.MatLike,
    pos=(0, 0),
    offset=0,
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False
):
    if (cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0)) and not no_crop:
        image = crop_image(image, cropped_pos1, cropped_pos2)
    pos = (pos[0] - cropped_pos1[0], pos[1] - cropped_pos1[1])
    color = image[pos[1], pos[0]]
    return BGR(*color, offset=offset)


def get_hsv(
    image: cv.typing.MatLike,
    pos=(0, 0),
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False
):
    if (cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0)) and not no_crop:
        image = crop_image(image, cropped_pos1, cropped_pos2)
    image_hsv = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    pos = (pos[0] - cropped_pos1[0], pos[1] - cropped_pos1[1])
    color = image_hsv[int(pos[1]), int(pos[0])]
    return HSV(*color, offset=0)


def get_bgrs(
    image: cv.typing.MatLike,
    positions: List[Tuple[int, int]] = [(0, 0)],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False
):
    if (cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0)) and not no_crop:
        image = crop_image(image, cropped_pos1, cropped_pos2)
    new_positions = [
        (position[0] - cropped_pos1[0], position[1] - cropped_pos1[1])
        for position in positions
    ]
    new_positions: Any = [(position[1], position[0]) for position in positions]
    new_positions = np.array(new_positions)
    colors = image[new_positions[:, 0], new_positions[:, 1]]
    return [BGR(*color, offset=0) for color in colors]


def show_image(image: cv.typing.MatLike, name="image", time=0):
    cv.namedWindow(name)
    cv.imshow(name, image)
    cv.waitKey(time)
    cv.destroyAllWindows()


def save_image(image: cv.typing.MatLike, path: Union[str, Path]):
    if isinstance(path, Path):
        path = str(path)
    cv.imwrite(path, image)
