from typing import Optional, Set

from resonance.scene.scene import Scene
from resonance.vision.ocr import merge_ocr_text


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    _, text = merge_ocr_text(ocr_results)

    if "前往目的地" in text:
        detail_markers = ("路程", "推荐等级", "发展度", "声望")
        if any(marker in text for marker in detail_markers):
            return Scene.STATION_DETAIL

    if "图示" in text and "前往目的地" not in text:
        return Scene.STATION_LIST

    return None
