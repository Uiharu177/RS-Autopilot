from pathlib import Path
from typing import Optional, Set

from resonance.scene.scene import Scene
from resonance.vision.utils import match_template


CITY_OUTLET_MARKERS = (
    "交易所",
    "商会",
    "市集",
    "工会",
    "俱乐部",
    "铁安局",
    "市政厅",
    "奶茶店",
    "研究所",
    "休息区",
    "市场",
)


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    outlet_hits = 0
    for item in ocr_results:
        text = item["text"]
        if any(marker in text for marker in CITY_OUTLET_MARKERS):
            outlet_hits += 1
    if outlet_hits >= 2:
        return Scene.CITY_VIEW

    if match_template(
        img,
        Path("resources/scene/fame.png"),
        cropped_pos1=(25, 634),
        cropped_pos2=(99, 707),
        threshold=0.95,
    ):
        return Scene.CITY_VIEW
    return None
