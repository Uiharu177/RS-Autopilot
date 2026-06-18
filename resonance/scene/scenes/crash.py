from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    text = "\n".join(text_set)
    if "EXIT GAME" in text or "Err0r" in text or "Error" in text:
        return Scene.CRASH
    return None
