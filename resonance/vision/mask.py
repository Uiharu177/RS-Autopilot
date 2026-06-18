"""主界面可点击区域 mask：过滤掉主地图上非交互区域，防止误点击。

  使用 pre-computed mask 图片（main_click_mask.png），
  对截图做 AND 操作后只有白色区域才允许点击。
"""

from functools import lru_cache
from pathlib import Path
from typing import Tuple

import cv2 as cv

from resonance.utils.utils import RESOURCES_PATH


MAIN_CLICK_MASK = RESOURCES_PATH / "mask" / "main_click_mask.png"


@lru_cache(maxsize=1)
def _load_main_click_mask():
    mask = cv.imread(str(MAIN_CLICK_MASK), cv.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(MAIN_CLICK_MASK)
    return mask


def is_main_clickable(pos: Tuple[int, int], threshold: int = 16) -> bool:
    """Return True when pos is in a black clickable area of the main-map mask."""
    x, y = int(pos[0]), int(pos[1])
    mask = _load_main_click_mask()
    height, width = mask.shape[:2]
    if x < 0 or y < 0 or x >= width or y >= height:
        return False
    return int(mask[y, x]) < threshold


def main_click_mask_path() -> Path:
    return MAIN_CLICK_MASK
