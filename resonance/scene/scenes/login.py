from pathlib import Path
from typing import Optional, Set

from resonance.scene.scene import Scene
from resonance.vision.utils import match_template


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    if match_template(img, Path("resources/scene/login.png"), threshold=0.95):
        return Scene.LOGIN

    login_markers = ("点击屏幕进入游戏", "点击进入", "TOUCH TO START", "TAP TO START")
    for item in ocr_results:
        text = item["text"].upper()
        if not any(marker in text for marker in login_markers):
            continue
        pos = item["position"]
        center_x = (pos[0][0] + pos[2][0]) / 2
        center_y = (pos[0][1] + pos[2][1]) / 2
        if 260 <= center_y <= 650 and 220 <= center_x <= 1060:
            return Scene.LOGIN
    return None
