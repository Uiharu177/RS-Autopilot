from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    if "弃牌" in text_set:
        return Scene.BATTLE_CARD

    # MAX can appear in non-battle UI/OCR noise during travel; do not let it
    # trigger battle detection by itself.
    card_markers = {"费用", "抽牌", "出牌", "回合", "能量"}
    if ("max" in text_set or "MAX" in text_set) and any(marker in text_set for marker in card_markers):
        return Scene.BATTLE_CARD
    return None
