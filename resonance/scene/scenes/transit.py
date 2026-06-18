from typing import Optional, Set

import cv2 as cv

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    if gray.mean() < 40:
        return Scene.TRANSIT
    return None
