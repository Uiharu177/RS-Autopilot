from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    loading_markers = (
        "加载中",
        "正在加载",
        "资源加载",
        "Loading",
        "LOADING",
    )
    if any(marker in text for text in text_set for marker in loading_markers):
        return Scene.LOADING
    return None
