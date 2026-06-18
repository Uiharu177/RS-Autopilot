from typing import Optional, Set

from resonance.scene.scene import Scene
from resonance.vision.ocr import merge_ocr_text


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    main_markers = {"启程", "START ENGINE", "整备列车", "客运管理"}
    if main_markers & text_set:
        return None

    _, text = merge_ocr_text(ocr_results)
    has_cruise = "自动巡航中" in text
    has_travel = "目的地" in text or "剩余行程" in text

    if has_cruise:
        return Scene.TRAVEL_CRUISE
    if has_travel:
        return Scene.TRAVEL_MAP
    return None
