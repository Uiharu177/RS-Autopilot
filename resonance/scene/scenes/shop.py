from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    if "我要买" in text_set or "购买" in text_set:
        return Scene.SHOP
    return None
