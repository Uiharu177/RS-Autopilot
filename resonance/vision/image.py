"""图像封装：在 OpenCV Mat 上提供裁剪、模板匹配、颜色读取、OCR 的便捷接口。

  Image 包装 cv.Mat，支持链式调用：
    screenshot().crop_image(...).get_bgr(pos)
    screenshot().match_template(template, threshold)
    screenshot().ocr() 等
"""

from pathlib import Path
from typing import List, Tuple, Union

import cv2 as cv

from resonance.vision.ocr import number_predict, predict
from resonance.vision.utils import MATCH_TEMPLATE_RESULT, crop_image, get_bgr, get_bgrs, get_hsv, match_template, save_image, show_image
from resonance.vision.color import BGR


class Image:
    def __init__(self, image: cv.typing.MatLike):
        self.image = image
        self.cropped_pos1 = (0, 0)
        self.cropped_pos2 = (0, 0)

    def crop_image(
        self,
        cropped_pos1: Tuple[int, int] = (0, 0),
        cropped_pos2: Tuple[int, int] = (0, 0),
    ):
        self.cropped_pos1 = cropped_pos1
        self.cropped_pos2 = cropped_pos2
        self.image = crop_image(self.image, cropped_pos1, cropped_pos2)
        return self

    def match_template(
        self,
        template: Union[str, Path, cv.typing.MatLike],
        threshold: float = 0.8,
    ) -> MATCH_TEMPLATE_RESULT:
        return match_template(self.image, template, self.cropped_pos1, self.cropped_pos2, threshold, no_crop=True)

    def get_bgr(self, pos=(0, 0), offset=0):
        return get_bgr(self.image, pos, offset, self.cropped_pos1, self.cropped_pos2, no_crop=True)

    def get_hsv(self, pos=(0, 0)):
        return get_hsv(self.image, pos, self.cropped_pos1, self.cropped_pos2, no_crop=True)

    def get_bgrs(self, positions: List[Tuple[int, int]] = [(0, 0)]):
        return get_bgrs(self.image, positions, self.cropped_pos1, self.cropped_pos2, no_crop=True)

    def show_image(self, name="image", time=0):
        show_image(self.image, name, time)

    def save_image(self, path: Union[str, Path]):
        save_image(self.image, path)

    def ocr(self):
        return predict(self.image, self.cropped_pos1, self.cropped_pos2, no_crop=True)

    def number_ocr(self):
        return number_predict(self.image, self.cropped_pos1, self.cropped_pos2, no_crop=True)
