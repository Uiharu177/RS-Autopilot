from pathlib import Path
from typing import Optional, Set

from resonance.scene.scene import Scene
from resonance.vision.utils import match_template


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    if match_template(img, Path("resources/scene/main_map.png"), threshold=0.96):
        return Scene.MAIN_MAP
    return None
